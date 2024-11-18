import os
from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorCollection,
)
from common import logger


def load_db() -> tuple[AsyncIOMotorCollection, AsyncIOMotorCollection] | None:
    db_connection = os.environ.get("DB_CONNECTION_STRING", None)
    db_name = os.environ.get("DB_NAME", None)
    if db_name is None or db_connection is None:
        logger.info(
            "DB config incomplete, either missing DB_CONNECTION_STRING or DB_NAME from environment variables"
        )
        return None
    db_client = AsyncIOMotorClient(db_connection)
    database = db_client[db_name]
    playtime_collection = database["playtime"]
    live_sessions_collection = database["live_session"]
    return (live_sessions_collection, playtime_collection)
