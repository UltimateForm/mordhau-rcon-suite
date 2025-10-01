from reactivex import Observer
from motor.motor_asyncio import AsyncIOMotorCollection
from common.gc_shield import backtask
from persistent_titles.data import SessionEvent
from common import logger


class PlaytimeClient(Observer[SessionEvent]):
    _collection: AsyncIOMotorCollection

    def __init__(self, collection: AsyncIOMotorCollection) -> None:
        self._collection = collection
        super().__init__()

    async def add_playtime(self, user_name: str, playfab_id: str, minutes: int):
        update = await self._collection.update_one(
            {"playfab_id": playfab_id},
            {
                "$set": {"playfab_id": playfab_id, "user_name": user_name},
                "$inc": {"minutes": minutes},
            },
            upsert=True,
        )
        if not update.acknowledged:
            logger.error(
                f"Failed to add playtime ({minutes} mins) to playfab id {playfab_id}"
            )

    async def get_playtime(self, playfab_id: str) -> int:
        read = await self._collection.find_one({"playfab_id": playfab_id})
        return read.get("minutes", 0) if read else 0

    def on_next(self, value: SessionEvent):
        backtask(self.add_playtime(value.user_name, value.playfab_id, value.minutes))
