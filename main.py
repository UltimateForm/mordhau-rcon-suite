import asyncio
from dc_player_commands.main import register_dc_player_commands
from config_client.data import pt_config as p_config, bot_config as b_config
from dotenv import load_dotenv
from boards.info import InfoBoard
from boards.kills import KillsScoreboard
from boards.season import SeasonScoreboard
from common import logger
from common.models import LoginEvent, PlayerStore, KillfeedEvent, ChatEvent
from common.discord import ObservableDiscordClient, common_intents
from ingame_cmd.main import IngameCommands
from persistent_titles.main import PersistentTitles
from migrant_titles.main import MigrantTitles, MigrantComputeEvent
from rcon.rcon_listener import RconListener
from db_kills.main import DbKills
from boards.playtime import PlayTimeScoreboard
from killstreaks.main import KillStreaks
from discord.ext.commands import Bot
from reactivex import operators, Observable, empty
from common.parsers import (
    parse_chat_event,
    parse_login_event,
    parse_killfeed_event,
    parse_matchstate,
)
from config_client.models import BotConfig, PtConfig, SeasonConfig
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorClient
from typing import Coroutine
from monitoring.chat_logs import ChatLogs
from seasons.dc_config import register_season_cfg_commands
from seasons.season_controller import SEASON_TOPIC

load_dotenv()

# TODO: reactive suite components instead of stupid setup methods


class MordhauRconSuite:
    tasks: set[Coroutine] = set()
    login_events: Observable[LoginEvent | None] = empty()
    killfeed_events: Observable[KillfeedEvent | None] = empty()
    chat_events: Observable[ChatEvent | None] = empty()
    matchstate_events: Observable[str | None] = empty()
    _bot_config: BotConfig
    _pt_config: PtConfig
    _dc_bot: Bot
    _dc_client: ObservableDiscordClient
    _database: AsyncIOMotorDatabase
    migrant_titles: MigrantTitles
    peristent_titles: PersistentTitles
    ingame_commands: IngameCommands
    player_store: PlayerStore
    db_kills: DbKills
    killstreaks: KillStreaks | None = None
    playtime_scoreboard: PlayTimeScoreboard
    info_scoreboard: InfoBoard | None = None
    kills_scoreboard: KillsScoreboard
    season_scoreboard: SeasonScoreboard
    _initial_season_cfg: SeasonConfig | None = None

    @property
    def playtime_collection(self):
        return self._database["playtime"]

    @property
    def live_sessions_collection(self):
        return self._database["live_session"]

    @property
    def kills_collection(self):
        return self._database["kills"]

    def __init__(self, bot_config: BotConfig, pt_config: PtConfig):
        self._bot_config = bot_config
        self._pt_config = pt_config
        if SeasonConfig.exists():
            self._initial_season_cfg = SeasonConfig.load()
        self.set_up_db()
        self.set_up_discord()
        if self._bot_config.experimental_bulk_listener:
            self.set_up_bulk_listeners()
        else:
            self.set_up_listeners()
        self.set_up_experiences()
        self.set_up_boards()
        self.set_up_monitoring()

    def _entrance_desk(self, player: LoginEvent | None):
        try:
            if player is None:
                return
            if player.instance == "out":
                if self.migrant_titles.rex_compute.current_rex == player.player_id:
                    self.migrant_titles.rex_compute.current_rex = ""
                self.player_store.players.pop(player.player_id, None)
                if self.killstreaks:
                    asyncio.create_task(
                        self.killstreaks.self_end_ks(player.user_name, player.player_id)
                    )
            else:
                self.player_store.players[player.player_id] = player.user_name
        except Exception as e:
            logger.error(
                f"Failed to populate player store with event '{player}'; Error: {e}"
            )

    def _handle_tag_for_removed_rex(self, event: MigrantComputeEvent):
        logger.debug(f"handle_tag_for_removed_rex {event}")
        if event.event_type != "removed":
            return
        asyncio.create_task(
            self.peristent_titles.login_observer.handle_tag(
                LoginEvent("Login", "", event.user_name, event.playfab_id, "in")
            )
        )

    def set_up_boards(self):
        playtime_channel = self._bot_config.playtime_channel
        kills_channel = self._bot_config.kills_channel
        self.playtime_scoreboard = PlayTimeScoreboard(
            self.playtime_collection,
            playtime_channel,
            self._bot_config.playtime_refresh_time,
        )
        self.kills_scoreboard = KillsScoreboard(
            self.kills_collection, kills_channel, self._bot_config.kills_refresh_time
        )
        self.season_scoreboard = SeasonScoreboard(
            self.kills_collection,
            self._bot_config.kills_refresh_time,
            self._initial_season_cfg,
        )
        if self._bot_config.info_board_enabled():
            self.info_board = InfoBoard(
                self._bot_config.info_channel or 0, self._bot_config.info_refresh_time
            )
            self._dc_client.subscribe(self.info_board)
        self._dc_client.subscribe(self.playtime_scoreboard)
        self._dc_client.subscribe(self.kills_scoreboard)
        self._dc_client.subscribe(self.season_scoreboard)

    def set_up_experiences(self):
        self.player_store = PlayerStore()
        self.migrant_titles = MigrantTitles(self.killfeed_events, self.player_store)
        self.peristent_titles = PersistentTitles(
            self.login_events,
            self._dc_bot,
            self.playtime_collection,
            self.live_sessions_collection,
        )

        def reset_migrant_title(state: str | None):
            if not state:
                return
            if state.lower() == "in progress":
                self.migrant_titles.rex_compute.current_rex = ""

        self.matchstate_events.subscribe(reset_migrant_title)
        self.ingame_commands = IngameCommands(self._pt_config, self._database)
        self.db_kills = DbKills(
            self.kills_collection,
            self.killfeed_events,
            self.player_store,
            self._initial_season_cfg,
        )

        self.chat_events.subscribe(self.ingame_commands)
        self.login_events.subscribe(self._entrance_desk)
        self.migrant_titles.rex_compute.subscribe(self._handle_tag_for_removed_rex)

        register_season_cfg_commands(self._dc_bot, self._bot_config)
        SEASON_TOPIC.subscribe(lambda x: logger.info(f"Season event {x}"))
        if self._bot_config.ks_enabled:
            self.killstreaks = KillStreaks()

            def matchstate_next(state: str | None):
                if not state:
                    return
                if state.lower() == "in progress" and self.killstreaks:
                    self.killstreaks.reset()

            self.matchstate_events.subscribe(matchstate_next)
            self.killfeed_events.subscribe(self.killstreaks)

        self.tasks.add(self.db_kills.start())

    def set_up_monitoring(self):
        if not self._bot_config.chat_logs_channel:
            return
        chat_logs = ChatLogs(
            self._dc_client, self._bot_config.chat_logs_channel, self._dc_bot
        )
        self.chat_events.subscribe(chat_logs)

    def set_up_db(self):
        db_connection = self._bot_config.db_connection_string
        db_name = self._bot_config.db_name
        if db_name is None or db_connection is None:
            logger.info(
                "DB config incomplete, either missing DB_CONNECTION_STRING or DB_NAME from environment variables"
            )
            return None
        db_client = AsyncIOMotorClient(db_connection)
        self._database = db_client[db_name]

    def set_up_discord(self):
        self._dc_bot = Bot(
            command_prefix=".", intents=common_intents, help_command=None
        )
        d_token = self._bot_config.d_token
        self._dc_client = ObservableDiscordClient(intents=common_intents)
        register_dc_player_commands(self._dc_bot, self._database)
        self.tasks.update(
            [self._dc_bot.start(token=d_token), self._dc_client.start(token=d_token)]
        )

    def set_up_bulk_listeners(self):
        events_to_listen = ["login", "killfeed", "chat", "matchstate"]
        bulk_listener = RconListener(event=events_to_listen)
        self.login_events = bulk_listener.pipe(
            operators.filter(lambda x: x.startswith("Login")),
            operators.map(parse_login_event),
        )
        self.killfeed_events = bulk_listener.pipe(
            operators.filter(lambda x: x.startswith("Killfeed")),
            operators.map(parse_killfeed_event),
        )
        self.chat_events = bulk_listener.pipe(
            operators.filter(lambda x: x.startswith("Chat")),
            operators.map(parse_chat_event),
            operators.filter(lambda x: x is not None),
        )
        self.matchstate_events = bulk_listener.pipe(
            operators.filter(lambda x: x.startswith("MatchState")),
            operators.map(parse_matchstate),
        )
        self.tasks.add(bulk_listener.start())

    def set_up_listeners(self):
        chat_listener = RconListener("chat")
        killfeed_listener = RconListener("killfeed")
        login_listener = RconListener("login")
        matchstate_listener = RconListener("matchstate")
        self.login_events = login_listener.pipe(
            operators.map(parse_login_event),
        )
        self.killfeed_events = killfeed_listener.pipe(
            operators.map(parse_killfeed_event),
        )
        self.chat_events = chat_listener.pipe(
            operators.map(parse_chat_event),
        )
        self.matchstate_events = matchstate_listener.pipe(
            operators.map(parse_matchstate)
        )
        self.tasks.update(
            [
                chat_listener.start(),
                killfeed_listener.start(),
                login_listener.start(),
                matchstate_listener.start(),
            ]
        )

    async def start(self):
        try:
            await asyncio.gather(*self.tasks)
        finally:
            await self.close_db()

    async def close_db(self):
        if self._database is not None:
            self._database.client.close()


if __name__ == "__main__":
    logger.use_date_time_logger()
    logger.info("INIT")
    suite = MordhauRconSuite(b_config, p_config)
    asyncio.run(suite.start())
    logger.info("END")
