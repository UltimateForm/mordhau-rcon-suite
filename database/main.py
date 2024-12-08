from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorDatabase,
)
from common import logger
from config_client.data import bot_config

LOADED_DB: AsyncIOMotorDatabase = None


def load_db() -> AsyncIOMotorDatabase:
    db_connection = bot_config.db_connection_string
    db_name = bot_config.db_name
    if db_name is None or db_connection is None:
        logger.info(
            "DB config incomplete, either missing DB_CONNECTION_STRING or DB_NAME from environment variables"
        )
        return None
    db_client = AsyncIOMotorClient(db_connection)
    database = db_client[db_name]
    return database
