import asyncio
from reactivex import Observer

from common.compute import compute_gate_text, compute_next_gate_text, compute_time_txt
from common.models import ChatEvent
from config_client.models import PtConfig, SeasonConfig
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection

from rank_compute.kills import get_kills, get_season_kills
from rank_compute.playtime import get_playtime
from rcon.rcon import RconContext


class IngameCommands(Observer[ChatEvent | None]):
    _config: PtConfig
    _playtime_collection: AsyncIOMotorCollection
    _kills_collection: AsyncIOMotorCollection

    def __init__(self, config: PtConfig, db: AsyncIOMotorDatabase) -> None:
        self._playtime_collection = db["playtime"]
        self._kills_collection = db["kills"]
        self._config = config
        super().__init__()

    async def handle_playtime(self, playfab_id: str, user_name: str):
        user_playtime = await get_playtime(playfab_id, self._playtime_collection)
        full_msg = ""
        if user_playtime is None or user_playtime.minutes < 1:
            full_msg = f"{user_name} has no recorded playtime"
        else:
            full_msg = f"{user_playtime.user_name} is PLAYTIME RANKED {user_playtime.rank + 1}\n{user_playtime.time_txt} played"
        async with RconContext() as client:
            await client.execute(f"say {full_msg}")

    async def handle_rank(self, playfab_id: str, user_name: str):
        user_playtime = await get_playtime(playfab_id, self._playtime_collection)
        if user_playtime is None or user_playtime.minutes < 1:
            full_msg = f"{user_name} has no recorded playtime"
        else:
            global_rank = self._config.tags.get("*", None)
            full_msg = ""
            (_, rank_txt) = compute_gate_text(
                user_playtime.minutes, self._config.playtime_tags
            )
            full_msg += (
                f"{user_playtime.user_name} playtime rank: {rank_txt or global_rank}"
            )
            (next_rank_minutes, next_rank_txt) = compute_next_gate_text(
                user_playtime.minutes, self._config.playtime_tags
            )
            if next_rank_txt is not None and next_rank_minutes is not None:
                full_msg += (
                    f"; Next: {next_rank_txt} at {compute_time_txt(next_rank_minutes)}"
                )
        async with RconContext() as client:
            await client.execute(f"say {full_msg}")

    async def handle_kdr(self, playfab_id: str, user_name: str):
        user_kdr = await get_kills(playfab_id, self._kills_collection)
        full_msg: str = ""
        if user_kdr is None:
            full_msg = f"{user_name} has no recorded kdr"
        else:
            rank_cmp = user_kdr.rank + 1 if user_kdr.rank is not None else "N/A"
            full_msg = f"{user_kdr.user_name} is KDR RANKED {rank_cmp}\nKills {user_kdr.kill_count} | Deaths {user_kdr.death_count} | Ratio {user_kdr.ratio} "
        async with RconContext() as client:
            await client.execute(f"say {full_msg}")

    async def handle_versus(self, playfab_id: str, user_name: str, argument: str):
        self_kdr = await get_kills(playfab_id, self._kills_collection, get_rank=False)
        other_kdr = await get_kills(argument, self._kills_collection, get_rank=False)
        full_msg: str = ""
        if self_kdr is None:
            full_msg = f"{user_name} has no recorded kdr"
        elif other_kdr is None:
            full_msg = f"{argument} has no recorded kdr"
        else:
            player_1_kills = self_kdr.kills.get(other_kdr.player_id, 0)
            player_2_kills = other_kdr.kills.get(self_kdr.player_id, 0)
            full_msg = f"{self_kdr.user_name} {player_1_kills} vs {player_2_kills} {other_kdr.user_name}"
        async with RconContext() as client:
            await client.execute(f"say {full_msg}")

    async def handle_skdr(self, playfab_id: str, user_name: str):
        full_msg: str = ""
        exists = await SeasonConfig.aexists()
        if not exists:
            full_msg = "No active season"
        season_cfg = await SeasonConfig.aload()
        if not season_cfg.is_active:
            full_msg = "No active season"
        if not full_msg:
            user_kdr = await get_season_kills(
                playfab_id, self._kills_collection, season_cfg
            )
            if user_kdr is None:
                full_msg = f"{user_name} has no recorded season kdr"
            else:
                rank_cmp = user_kdr.rank + 1 if user_kdr.rank is not None else "N/A"
                full_msg = (
                    f"{user_kdr.user_name} is KDR RANKED {rank_cmp} in "
                    f"{season_cfg.embed_config.title or season_cfg.name}\n"
                    f"Kills {user_kdr.kill_count} | Deaths {user_kdr.death_count} | "
                    f"Ratio {user_kdr.ratio} "
                )
        async with RconContext() as client:
            await client.execute(f"say {full_msg}")

    def on_next(self, event_data: ChatEvent | None) -> None:
        if not event_data:
            return
        message = event_data.message.rstrip()
        if not message.startswith("."):
            return
        playfab_id = event_data.player_id
        user_name = event_data.user_name
        if message == ".playtime":
            asyncio.create_task(self.handle_playtime(playfab_id, user_name))
        elif message == ".rank":
            asyncio.create_task(self.handle_rank(playfab_id, user_name))
        elif message == ".kdr":
            asyncio.create_task(self.handle_kdr(playfab_id, user_name))
        elif message == ".skdr":
            asyncio.create_task(self.handle_skdr(playfab_id, user_name))
        elif message.startswith(".versus") or message.startswith(".vs"):
            split_versus = message.split(" ", 1)
            if len(split_versus) < 2:
                return
            asyncio.create_task(
                self.handle_versus(playfab_id, user_name, split_versus[1])
            )
