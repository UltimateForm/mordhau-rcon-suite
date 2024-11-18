from os import environ
import asyncio
from reactivex import Observer
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorClient
from persistent_titles.data import SessionEvent
from common import logger


class PlaytimeClient(Observer[SessionEvent]):
    _collection: AsyncIOMotorCollection

    def __init__(self, collection: AsyncIOMotorCollection) -> None:
        self._collection = collection
        super().__init__()

    async def add_playtime(self, playfab_id: str, minutes: int):
        update = await self._collection.update_one(
            {"playfab_id": playfab_id},
            {
                "$set": {
                    "playfab_id": playfab_id,
                },
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
        asyncio.create_task(self.add_playtime(value.playfab_id, value.minutes))


async def main():
    logger.use_date_time_logger()
    db_connection = environ.get("DB_CONNECTION_STRING", None)
    db_name = environ.get("DB_NAME", None)
    db_client = AsyncIOMotorClient(db_connection)
    database = db_client[db_name]
    collection = database["playtime"]
    playtime_client = PlaytimeClient(collection)
    await playtime_client.add_playtime("AS81236657AKMD", 10)
    await asyncio.sleep(5)
    await playtime_client.add_playtime("AS81236657AKMD", 20)
    await asyncio.sleep(5)
    playtime = await playtime_client.get_playtime("AS81236657AKMD")
    logger.debug(f"Playtime: {playtime}")


if __name__ == "__main__":
    asyncio.run(main())
