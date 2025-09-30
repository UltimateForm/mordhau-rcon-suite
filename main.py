import asyncio
from dc_player_commands.main import register_dc_player_commands
from config_client.data import pt_config as p_config, bot_config as b_config
from dotenv import load_dotenv
from boards.info import InfoBoard
from boards.kills import KillsScoreboard
from boards.season import SeasonScoreboard
from boards.dc_config import BoardCommands
from common import logger
from common.models import LoginEvent, PlayerStore, KillfeedEvent, ChatEvent
from common.discord import ObservableDiscordClient, common_intents, BotHelper
from ingame_cmd.main import IngameCommands
from persistent_titles.main import PersistentTitles
from migrant_titles.main import MigrantTitles, MigrantComputeEvent
from rcon.rcon_listener import RconListener
from rcon.rcon_pool import RconConnectionPool
from db_kills.main import DbKills
from boards.playtime import PlayTimeScoreboard
from killstreaks.main import KillStreaks
from discord.ext.commands import Bot, Cog
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
from seasons.dc_config import SeasonAdminCommands
from seasons.season_controller import SEASON_TOPIC, SeasonWatch
from dc_db_config.main import DcDbConfig

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
    migrant_titles: MigrantTitles | None = None
    peristent_titles: PersistentTitles
    ingame_commands: IngameCommands
    player_store: PlayerStore
    db_kills: DbKills
    killstreaks: KillStreaks | None = None
    _initial_season_cfg: SeasonConfig | None = None
    rcon_pool: RconConnectionPool

    @property
    def playtime_collection(self):
        return self._database["playtime"]

    @property
    def live_sessions_collection(self):
        return self._database["live_session"]

    @property
    def kills_collection(self):
        return self._database["kills"]

    def __init__(
        self,
        bot_config: BotConfig,
        pt_config: PtConfig,
        loop: asyncio.AbstractEventLoop,
    ):
        self._bot_config = bot_config
        self._pt_config = pt_config
        self.rcon_pool = RconConnectionPool(3)
        if SeasonConfig.exists():
            self._initial_season_cfg = SeasonConfig.load()
        self.set_up_db()
        self.set_up_discord(loop)
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
                if (
                    self.migrant_titles
                    and self.migrant_titles.rex_compute.current_rex == player.player_id
                ):
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
        cogs: list[Cog] = []
        if self._bot_config.playtime_board_enabled():
            playtime_scoreboard = PlayTimeScoreboard(
                self._dc_bot,
                self.playtime_collection,
                playtime_channel,
                self._bot_config.playtime_refresh_time,
            )
            cogs.append(playtime_scoreboard)
        if self._bot_config.kills_board_enabled():
            kills_scoreboard = KillsScoreboard(
                self._dc_bot,
                self.kills_collection,
                kills_channel,
                self._bot_config.kills_refresh_time,
            )
            cogs.append(kills_scoreboard)
        if self._bot_config.season_board_enabled():
            season_scoreboard = SeasonScoreboard(
                self._dc_bot,
                self.kills_collection,
                self._bot_config.kills_refresh_time,
                self._initial_season_cfg,
            )
            cogs.append(season_scoreboard)
        cogs.append(BoardCommands(self._dc_bot, self._bot_config))
        if self._bot_config.info_board_enabled():
            info_board = InfoBoard(
                self.rcon_pool,
                self._dc_bot,
                self._bot_config.info_channel or 0,
                self._bot_config.info_refresh_time,
            )
            cogs.append(info_board)
        for cog in cogs:
            self._dc_bot.add_cog(cog)

    def set_up_experiences(self):
        self.player_store = PlayerStore()
        if self._bot_config.title:
            self.migrant_titles = MigrantTitles(
                self.killfeed_events, self.player_store, self.rcon_pool
            )

            def reset_migrant_title(state: str | None):
                if not state:
                    return
                if state.lower() == "in progress" and self.migrant_titles:
                    self.migrant_titles.rex_compute.current_rex = ""

            self.matchstate_events.subscribe(reset_migrant_title)
            self.migrant_titles.rex_compute.subscribe(self._handle_tag_for_removed_rex)
        self.peristent_titles = PersistentTitles(
            self.rcon_pool,
            self.login_events,
            self._dc_bot,
            self.playtime_collection,
            self.live_sessions_collection,
        )

        self.ingame_commands = IngameCommands(
            self._pt_config, self._database, self.rcon_pool
        )
        self.db_kills = DbKills(
            self.kills_collection,
            self.killfeed_events,
            self.player_store,
            self._initial_season_cfg,
        )
        self.chat_events.subscribe(self.ingame_commands)
        self.login_events.subscribe(self._entrance_desk)

        SEASON_TOPIC.subscribe(lambda x: logger.info(f"Season event {x}"))
        SEASON_TOPIC.subscribe(
            SeasonWatch(self.kills_collection, self._initial_season_cfg)
        )
        if self._bot_config.ks_enabled:
            self.killstreaks = KillStreaks(self.rcon_pool)

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
            self._dc_client, self._bot_config, self._dc_bot, self.rcon_pool
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

    def set_up_discord(self, loop: asyncio.AbstractEventLoop):
        self._dc_bot = Bot(
            command_prefix=".", intents=common_intents, help_command=None, loop=loop
        )
        d_token = self._bot_config.d_token
        self._dc_client = ObservableDiscordClient(intents=common_intents, loop=loop)
        register_dc_player_commands(self._dc_bot, self._database, self.rcon_pool)
        self._dc_bot.add_cog(
            DcDbConfig(
                self._dc_bot,
                self._bot_config,
                self.playtime_collection,
                self.kills_collection,
            )
        )
        self._dc_bot.add_cog(BotHelper(self._dc_bot, self._bot_config))
        self._dc_bot.add_cog(SeasonAdminCommands(self._dc_bot, self._bot_config))
        self.tasks.update(
            [
                self._dc_bot.start(token=d_token),
                self._dc_client.start(token=d_token),
            ]
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
    loop = asyncio.get_event_loop()
    asyncio.set_event_loop(loop)
    suite = MordhauRconSuite(b_config, p_config, loop)
    loop.run_until_complete(suite.start())
    logger.info("END")
    loop.close()
    asyncio.set_event_loop(None)
