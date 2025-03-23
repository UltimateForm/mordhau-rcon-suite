import reactivex
from enum import Enum
from motor.motor_asyncio import (
    AsyncIOMotorCollection,
)
import asyncio

from common import logger
from config_client.models import SeasonConfig
from rank_compute.kills import update_achieved_ranks


class SeasonEvent(Enum):
    START = 1
    END = 2
    UPDATE = 3
    CREATE = 4
    DESTROY = 5


SEASON_TOPIC: reactivex.Subject[SeasonEvent] = reactivex.Subject()


class SeasonWatch(reactivex.Observer[SeasonEvent]):
    _kills_collection: AsyncIOMotorCollection
    _season_config: SeasonConfig | None

    def __init__(
        self, collection: AsyncIOMotorCollection, initial_config: SeasonConfig | None
    ):
        self._kills_collection = collection
        self._season_config = initial_config

    def on_next(self, value: SeasonEvent):
        if (
            value == SeasonEvent.UPDATE
            or value == SeasonEvent.CREATE
            or value == SeasonEvent.START
        ):
            asyncio.create_task(self.load_config())
        elif value == SeasonEvent.END:
            asyncio.create_task(self.on_season_end())

    async def load_config(self):
        try:
            self._season_config = await SeasonConfig.aload()
        except Exception as e:
            logger.error(f"{SeasonWatch.__name__}: Error loading season config: {e}")

    async def on_season_end(self):
        try:
            if not self._season_config:
                self._season_config = await SeasonConfig.aload()
            if not self._season_config.start_date:
                raise ValueError("Unable to end a season that has not started")
            top_20_items: list[dict] = (
                await self._kills_collection.find(
                    {f"season.{self._season_config.name}": {"$exists": True}}
                )
                .sort(f"season.{self._season_config.name}.kill_count", -1)
                .limit(20)
                .to_list()
            )
            await update_achieved_ranks(
                [
                    {"playfab_id": item["playfab_id"], "rank": index + 1}
                    for (index, item) in enumerate(top_20_items)
                ],
                self._kills_collection,
                self._season_config,
            )
        except Exception as e:
            logger.error(
                f"{SeasonWatch.__name__}: Error during season end processing: {e}"
            )
