import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorCollection
from reactivex import operators
from reactivex import Observable
from persistent_titles.database import load_db
from persistent_titles.login_observer import LoginObserver
from persistent_titles.chat_observer import ChatObserver
from persistent_titles.session_topic import SessionTopic
from persistent_titles.playtime_client import PlaytimeClient
from common.parsers import GROK_LOGIN_EVENT, parse_date, parse_event
from rcon.rcon_listener import RconListener
from common import logger
from config_client.main import config, config_bot


class PersistentTitles:
    login_observer: LoginObserver
    _login_observable: Observable[str]

    def __init__(self, login_observable: Observable[str]):
        self._login_observable = login_observable
        self.login_observer = LoginObserver(config)
        self._login_observable.pipe(
            operators.filter(lambda x: x.startswith("Login:"))
        ).subscribe(self.login_observer)

    def enable_playtime(
        self,
        playtime_client: PlaytimeClient,
        chat_listener: RconListener,
        live_sessions_collection: AsyncIOMotorCollection,
    ):
        chat_observer = ChatObserver(config, playtime_client)
        chat_listener.subscribe(chat_observer)
        session_topic = SessionTopic(live_sessions_collection)
        session_topic.subscribe(playtime_client)

        def session_topic_login_handler(event: str):
            (success, event_data) = parse_event(event, GROK_LOGIN_EVENT)
            if not success:
                logger.debug(f"Failure at parsing login event {event}")
                return
            logger.debug(f"LOGIN EVENT: {event_data}")
            order = event_data["order"]
            playfab_id = event_data["playfabId"]
            user_name = event_data["userName"]
            date = parse_date(event_data["date"])
            if order == "in":
                asyncio.create_task(session_topic.login(playfab_id, user_name, date))
            elif order == "out":
                asyncio.create_task(session_topic.logout(playfab_id, date))

        self._login_observable.pipe(
            operators.filter(lambda x: x.startswith("Login:"))
        ).subscribe(session_topic_login_handler)

    async def start(self):
        playtime_collection: AsyncIOMotorCollection | None = None
        playtime_client: PlaytimeClient | None = None
        live_sessions_collection: AsyncIOMotorCollection | None = None
        playtime_enabled = False
        db = load_db()
        if db:
            logger.info("Enabling playtime titles as DB is loaded")
            (live_sessions_collection, playtime_collection) = db
            playtime_client = PlaytimeClient(playtime_collection)
            playtime_enabled = True
        else:
            logger.info("Keeping playtime titles disabled as DB is not loaded")
        chat_listener = RconListener("chat")
        self.login_observer.playtime_client = playtime_client
        tasks = [config_bot.start(token=os.environ.get("D_TOKEN"))]
        if playtime_enabled:
            self.enable_playtime(
                playtime_client, chat_listener, live_sessions_collection
            )
            tasks.append(chat_listener.start())
        await asyncio.gather(*tasks)


async def main():
    login_listener = RconListener(event="login", listening=False)
    persistent_titles = PersistentTitles(login_listener)
    await asyncio.gather(login_listener.start(), persistent_titles.start())


if __name__ == "__main__":
    asyncio.run(main())
