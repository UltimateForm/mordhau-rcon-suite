from motor.motor_asyncio import AsyncIOMotorCollection
from reactivex import Observable
from common.gc_shield import backtask
from common.models import LoginEvent
from persistent_titles.login_observer import LoginObserver
from persistent_titles.session_topic import SessionTopic
from persistent_titles.playtime_client import PlaytimeClient
from persistent_titles.dc_config import register_cfg_dc_commands
from common.parsers import parse_date
from common import logger
from config_client.data import pt_config, bot_config
from discord.ext.commands import Bot

from rcon.rcon_pool import RconConnectionPool


class PersistentTitles:
    login_observer: LoginObserver | None
    _login_observable: Observable[LoginEvent | None]

    def __init__(
        self,
        rcon_pool: RconConnectionPool,
        login_observable: Observable[LoginEvent | None],
        bot: Bot | None = None,
        playtime_collection: AsyncIOMotorCollection | None = None,
        live_sessions_collection: AsyncIOMotorCollection | None = None,
    ):
        self._login_observable = login_observable
        if not bot_config.ingame_persistent_titles_disabled:
            self.login_observer = LoginObserver(rcon_pool, pt_config)
            self._login_observable.subscribe(self.login_observer)
        if bot:
            register_cfg_dc_commands(bot)

        playtime_client: PlaytimeClient | None = None
        if live_sessions_collection is not None and playtime_collection is not None:
            logger.info("Enabling playtime tracking as DB is loaded")
            playtime_client = PlaytimeClient(playtime_collection)
        else:
            logger.info("Keeping playtime tracking disabled as DB is not loaded")
        if self.login_observer:
            self.login_observer.playtime_client = playtime_client
        if (
            live_sessions_collection is not None
            and playtime_collection is not None
            and playtime_client is not None
        ):
            self.enable_playtime(playtime_client, live_sessions_collection)

    def enable_playtime(
        self,
        playtime_client: PlaytimeClient,
        live_sessions_collection: AsyncIOMotorCollection,
    ):
        session_topic = SessionTopic(live_sessions_collection)
        session_topic.subscribe(playtime_client)

        def session_topic_login_handler(event_data: LoginEvent | None):
            if not event_data:
                return
            order = event_data.instance
            playfab_id = event_data.player_id
            user_name = event_data.user_name
            date = parse_date(event_data.date)
            if order == "in":
                backtask(session_topic.login(playfab_id, user_name, date))
            elif order == "out":
                backtask(session_topic.logout(playfab_id, user_name, date))

        self._login_observable.subscribe(session_topic_login_handler)
