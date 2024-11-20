import os
from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorDatabase,
)
from common import logger

LOADED_DB: AsyncIOMotorDatabase = None


def load_db() -> AsyncIOMotorDatabase:
    db_connection = os.environ.get("DB_CONNECTION_STRING", None)
    db_name = os.environ.get("DB_NAME", None)
    if db_name is None or db_connection is None:
        logger.info(
            "DB config incomplete, either missing DB_CONNECTION_STRING or DB_NAME from environment variables"
        )
        return None
    db_client = AsyncIOMotorClient(db_connection)
    database = db_client[db_name]
    return database
