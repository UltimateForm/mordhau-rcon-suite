from motor.motor_asyncio import (
    AsyncIOMotorCollection,
)

from common import parsers
from common.models import PlaytimeScore
import re


async def get_playtime(
    argument: str, collection: AsyncIOMotorCollection
) -> PlaytimeScore | None:
    query: dict = {}
    if parsers.is_playfab_id_format(argument):
        query = {"playfab_id": argument}
    else:
        query = {"user_name": re.compile(f".*{argument}.*", re.IGNORECASE)}
    playtime_rec = await collection.find_one(query)
    if playtime_rec is None:
        return None
    user_name = playtime_rec.get("user_name", "<Unknown>")
    player_id = playtime_rec["playfab_id"]
    minutes = playtime_rec.get("minutes", 0)
    rank = await collection.count_documents({"minutes": {"$gt": minutes}})
    return PlaytimeScore(player_id, user_name, minutes, rank)
