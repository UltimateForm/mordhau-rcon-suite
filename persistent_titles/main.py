import asyncio
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
from reactivex import operators
from reactivex import Observable
from persistent_titles.login_observer import LoginObserver
from persistent_titles.session_topic import SessionTopic
from persistent_titles.playtime_client import PlaytimeClient
from persistent_titles.dc_config import register_cfg_dc_commands
from common.parsers import parse_date, parse_login_event
from rcon.rcon_listener import RconListener
from common import logger
from config_client.data import pt_config
from discord.ext.commands import Bot


class PersistentTitles:
    login_observer: LoginObserver
    _login_observable: Observable[str]

    def __init__(self, login_observable: Observable[str], bot: Bot | None = None):
        self._login_observable = login_observable
        self.login_observer = LoginObserver(pt_config)
        self._login_observable.pipe(
            operators.filter(lambda x: x.startswith("Login:"))
        ).subscribe(self.login_observer)
        if bot:
            register_cfg_dc_commands(bot)

    def enable_playtime(
        self,
        playtime_client: PlaytimeClient,
        live_sessions_collection: AsyncIOMotorCollection,
    ):
        session_topic = SessionTopic(live_sessions_collection)
        session_topic.subscribe(playtime_client)

        def session_topic_login_handler(event: str):
            event_data = parse_login_event(event)
            if not event_data:
                logger.debug(f"Failure at parsing login event {event}")
                return
            logger.debug(f"LOGIN EVENT: {event_data}")
            order = event_data.instance
            playfab_id = event_data.player_id
            user_name = event_data.user_name
            date = parse_date(event_data.date)
            if order == "in":
                asyncio.create_task(session_topic.login(playfab_id, user_name, date))
            elif order == "out":
                asyncio.create_task(session_topic.logout(playfab_id, user_name, date))

        self._login_observable.pipe(
            operators.filter(lambda x: x.startswith("Login:"))
        ).subscribe(session_topic_login_handler)

    async def start(
        self,
        db: AsyncIOMotorDatabase | None,
    ):
        playtime_collection: AsyncIOMotorCollection | None = None
        playtime_client: PlaytimeClient | None = None
        live_sessions_collection: AsyncIOMotorCollection | None = None
        playtime_enabled = False
        if db is not None:
            logger.info("Enabling playtime titles as DB is loaded")
            playtime_collection = db["playtime"]
            live_sessions_collection = db["live_session"]
            playtime_client = PlaytimeClient(playtime_collection)
            playtime_enabled = True
        else:
            logger.info("Keeping playtime titles disabled as DB is not loaded")
        self.login_observer.playtime_client = playtime_client
        if playtime_enabled:
            self.enable_playtime(playtime_client, live_sessions_collection)


async def main():
    login_listener = RconListener(event="login", listening=False)
    persistent_titles = PersistentTitles(login_listener)
    await asyncio.gather(login_listener.start(), persistent_titles.start())


if __name__ == "__main__":
    asyncio.run(main())
