from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorCollection
from reactivex import Subject
import pymongo
from persistent_titles.data import SessionEvent


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
        original_username = put["user_name"]
        session_duration = date - login_date
        session_minutes = session_duration.total_seconds() / 60
        session_minutes_rounded = round(session_minutes)
        self.on_next(
            SessionEvent(original_username, playfab_id, session_minutes_rounded)
        )
        return session_minutes_rounded
