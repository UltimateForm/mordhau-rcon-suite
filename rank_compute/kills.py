from motor.motor_asyncio import (
    AsyncIOMotorCollection,
)

from common import parsers
from common.models import KillScore
import re


async def get_kills(
    argument: str, collection: AsyncIOMotorCollection, get_rank: bool = True
) -> KillScore | None:
    query: dict = {}
    if parsers.is_playfab_id_format(argument):
        query = {"playfab_id": argument}
    else:
        query = {"user_name": re.compile(f".*{argument}.*", re.IGNORECASE)}
    kills_rec: dict = await collection.find_one(query)
    if kills_rec is None:
        return None
    user_name = kills_rec.get("user_name", "<Unknown>")
    player_id = kills_rec["playfab_id"]
    kill_count = kills_rec.get("kill_count", 0)
    kills = kills_rec.get("kills", {})
    rank = 0
    if get_rank:
        rank = await collection.count_documents({"kill_count": {"$gt": kill_count}})
    death_count = kills_rec.get("death_count", 0)
    return KillScore(player_id, user_name, kill_count, death_count, rank, kills)
