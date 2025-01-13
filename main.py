import asyncio
from dc_player_commands.main import register_dc_player_commands
from config_client.data import pt_config as p_config, bot_config as b_config
from dotenv import load_dotenv
from boards.info import InfoBoard
from boards.kills import KillsScoreboard
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
from config_client.models import BotConfig, PtConfig
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorClient
from typing import Coroutine

load_dotenv()

# TODO: reactive suite components instead of stupid setup methods


class MordhauRconSuite:
    tasks: set[Coroutine] = set()
    login_events: Observable[LoginEvent] = empty()
    killfeed_events: Observable[KillfeedEvent] = empty()
    chat_events: Observable[ChatEvent] = empty()
    matchstate_events: Observable[str] = empty()
    _bot_config: BotConfig = None
    _pt_config: PtConfig = None
    _dc_bot: Bot = None
    _dc_client: ObservableDiscordClient = None
    _database: AsyncIOMotorDatabase = None
    migrant_titles: MigrantTitles = None
    peristent_titles: PersistentTitles = None
    ingame_commands: IngameCommands = None
    player_store: PlayerStore = None
    db_kills: DbKills = None
    killstreaks: KillStreaks | None = None
    playtime_scoreboard: PlayTimeScoreboard = None
    info_scoreboard: InfoBoard | None = None
    kills_scoreboard: KillsScoreboard = None

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
        self.set_up_db()
        self.set_up_discord()
        if self._bot_config.experimental_bulk_listener:
            self.set_up_bulk_listeners()
        else:
            self.set_up_listeners()
        self.set_up_experiences()
        self.set_up_boards()

    def _entrance_desk(self, player: LoginEvent):
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
        if self._bot_config.info_board_enabled():
            self.info_board = InfoBoard(
                self._bot_config.info_channel, self._bot_config.info_refresh_time
            )
            self._dc_client.subscribe(self.info_board)
        self._dc_client.subscribe(self.playtime_scoreboard)
        self._dc_client.subscribe(self.kills_scoreboard)

    def set_up_experiences(self):
        self.player_store = PlayerStore()
        self.migrant_titles = MigrantTitles(self.killfeed_events, self.player_store)
        self.peristent_titles = PersistentTitles(
            self.login_events,
            self._dc_bot,
            self.playtime_collection,
            self.live_sessions_collection,
        )
        self.ingame_commands = IngameCommands(self._pt_config, self._database)
        self.db_kills = DbKills(
            self.kills_collection, self.killfeed_events, self.player_store
        )

        self.chat_events.subscribe(self.ingame_commands)
        self.login_events.subscribe(self._entrance_desk)
        self.migrant_titles.rex_compute.subscribe(self._handle_tag_for_removed_rex)

        if self._bot_config.ks_enabled:
            self.killstreaks = KillStreaks()

            def matchstate_next(state: str):
                if not state:
                    return
                stripped_state = state.strip("\x00")
                if stripped_state.lower() == "in progress":
                    self.killstreaks.reset()

            self.matchstate_events.subscribe(matchstate_next)
            self.killfeed_events.subscribe(self.killstreaks)

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
        events_to_listen = ["login", "killfeed", "chat"]
        if self._bot_config.ks_enabled:
            events_to_listen.append("matchstate")
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
        )
        self.matchstate_events = (
            bulk_listener.pipe(
                operators.filter(lambda x: x.startswith("MatchState")),
                operators.map(parse_matchstate),
            )
            if self._bot_config.ks_enabled
            else empty()
        )
        self.tasks.add(bulk_listener.start())

    def set_up_listeners(self):
        chat_listener = RconListener("chat")
        killfeed_listener = RconListener("killfeed")
        login_listener = RconListener("login")
        self.login_events = login_listener.pipe(
            operators.map(parse_login_event),
        )
        self.killfeed_events = killfeed_listener.pipe(
            operators.map(parse_killfeed_event),
        )
        self.chat_events = chat_listener.pipe(
            operators.map(parse_chat_event),
        )
        if self._bot_config.ks_enabled:
            matchstate_listener = RconListener("matchstate")
            self.matchstate_events = matchstate_listener.pipe(
                operators.map(parse_matchstate)
            )
            self.tasks.add(matchstate_listener.start())
        self.tasks.update(
            [
                chat_listener.start(),
                killfeed_listener.start(),
                login_listener.start(),
            ]
        )

    async def start(self):
        await asyncio.gather(*self.tasks)


if __name__ == "__main__":
    logger.use_date_time_logger()
    logger.info("INIT")
    suite = MordhauRconSuite(b_config, p_config)
    asyncio.run(suite.start())
    logger.info("END")
