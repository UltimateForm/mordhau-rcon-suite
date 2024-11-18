from os import environ
from datetime import datetime, timedelta
import asyncio
import dotenv
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorClient
from reactivex import Subject
import pymongo
from persistent_titles.data import SessionEvent
from common import logger, parsers


class SessionTopic(Subject[SessionEvent]):
    _collection: AsyncIOMotorCollection

    def __init__(self, collection: AsyncIOMotorCollection) -> None:
        self._collection = collection
        super().__init__()

    async def login(self, playfab_id: str, user_name: str, date: datetime) -> str:
        payload = {"playfab_id": playfab_id, "user_name": user_name, "login": date}
        write = await self._collection.insert_one(payload)
        if not write.acknowledged:
            raise ValueError(f"Could not create document for {playfab_id} at {date}")
        return str(write.inserted_id)

    async def logout(self, playfab_id: str, user_name: str, date: datetime) -> int:
        put = await self._collection.find_one_and_delete(
            {
                "playfab_id": playfab_id,
                "login": {"$gte": date - timedelta(hours=2)},
                "logout": {"$exists": False},
            },
            sort=[("login", pymongo.DESCENDING)],
        )
        if not put:
            raise ValueError(f"Failed to update session for {playfab_id} at {date}")
        login_date: datetime = put["login"]
        session_duration = date - login_date
        session_minutes = session_duration.total_seconds() / 60
        session_minutes_rounded = round(session_minutes)
        self.on_next(SessionEvent(user_name, playfab_id, session_minutes_rounded))
        return session_minutes_rounded


async def main():
    login_event = {
        "eventType": "Login",
        "date": "2024.06.21-23.05.13",
        "userName": "userName",
        "playfabId": "playfabId",
        "order": "out",
    }
    logout_event = {
        "eventType": "Login",
        "date": "2024.06.21-23.26.34",
        "userName": "userName",
        "playfabId": "playfabId",
        "order": "out",
    }
    logger.use_date_time_logger()
    dotenv.load_dotenv()

    db_connection = environ.get("DB_CONNECTION_STRING", None)
    db_name = environ.get("DB_NAME", None)
    db_client = AsyncIOMotorClient(db_connection)
    database = db_client[db_name]
    collection = database["live_sessions"]
    log_book = SessionTopic(collection)
    log_book.subscribe(lambda x: logger.debug(f"Session event: {x}"))
    session_id = await log_book.login(
        login_event["playfabId"],
        login_event["userName"],
        parsers.parse_date(login_event["date"]),
    )
    logger.debug(f"session id {session_id}")
    await asyncio.sleep(5)
    await log_book.logout(
        logout_event["playfabId"], parsers.parse_date(logout_event["date"])
    )


if __name__ == "__main__":
    asyncio.run(main())
