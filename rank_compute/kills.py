from motor.motor_asyncio import (
    AsyncIOMotorCollection,
)

from common import parsers
from common.models import KillScore
import re
from config_client.models import SeasonConfig
from pymongo import UpdateOne
from common import logger


async def get_kills(
    argument: str, collection: AsyncIOMotorCollection, get_rank: bool = True
) -> KillScore | None:
    query: dict = {}
    if parsers.is_playfab_id_format(argument):
        query = {"playfab_id": argument}
    else:
        query = {"user_name": re.compile(f".*{argument}.*", re.IGNORECASE)}
    kills_rec: dict | None = await collection.find_one(query)
    if kills_rec is None:
        return None
    user_name = kills_rec.get("user_name", "<Unknown>")
    player_id = kills_rec["playfab_id"]
    kill_count = kills_rec.get("kill_count", 0)
    kills = kills_rec.get("kills", {})
    achievements = kills_rec.get("achiev", {})
    rank = 0
    if get_rank:
        rank = await collection.count_documents({"kill_count": {"$gt": kill_count}})
    death_count = kills_rec.get("death_count", 0)
    return KillScore(
        player_id, user_name, kill_count, death_count, rank, kills, achievements
    )


async def get_season_kills(
    argument: str,
    collection: AsyncIOMotorCollection,
    season_config: SeasonConfig,
    get_rank: bool = True,
) -> KillScore | None:
    query: dict = {}
    if parsers.is_playfab_id_format(argument):
        query = {"playfab_id": argument}
    else:
        query = {"user_name": re.compile(f".*{argument}.*", re.IGNORECASE)}
    kills_rec: dict | None = await collection.find_one(query)
    if kills_rec is None:
        return None
    user_name = kills_rec.get("user_name", "<Unknown>")
    season_dict = kills_rec.get("season", {}).get(season_config.name, {})
    kill_count = season_dict.get("kill_count", 0)
    death_count = season_dict.get("death_count", 0)
    player_id = kills_rec["playfab_id"]
    kills = kills_rec.get("kills", {})
    rank = 0
    if get_rank:
        rank = await collection.count_documents(
            {f"season.{season_config.name}.kill_count": {"$gt": kill_count}}
        )
    return KillScore(player_id, user_name, kill_count, death_count, rank, kills)


async def update_achieved_ranks(
    records: list[dict],
    collection: AsyncIOMotorCollection,
    season: SeasonConfig | None = None,
):
    if not records or len(records) == 0:
        logger.debug("update_achieved_ranks receoved empty list, not doing anything")
        return
    tasks: list[UpdateOne] = []
    for record in records:
        mutation_key = f"achiev.{'lifetime_rank' if season is None else season.name}"
        update = UpdateOne(
            {"playfab_id": record["playfab_id"]},
            {"$min": {mutation_key: record["rank"]}},
            upsert=True,
        )
        tasks.append(update)
    bulk_update = await collection.bulk_write(tasks)
    logger.debug(
        f"update_achieved_ranks - Updated {len(tasks)} kill records: {bulk_update.bulk_api_result}"
    )
