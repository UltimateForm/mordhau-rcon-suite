import asyncio
import discord
from datetime import datetime, timezone
from motor.motor_asyncio import (
    AsyncIOMotorCollection,
)
from table2ascii import table2ascii as t2a
from boards.base import Board
from config_client.data import bot_config
from common.compute import compute_time_txt, human_format
from common.discord import make_embed
from rank_compute.kills import update_achieved_ranks

BOARD_REFRESH_TIME = bot_config.kills_refresh_time or 60


class KillsScoreboard(Board):
    _kills_collection: AsyncIOMotorCollection | None

    @property
    def file_path(self) -> str:
        return "./persist/kills_msg_id"

    def __init__(
        self,
        kills_collection: AsyncIOMotorCollection,
        channel_id,
        time_interval: int | None = 60,
    ):
        self._kills_collection = kills_collection
        super().__init__(channel_id, time_interval)

    def compute_kdr(self, record: dict) -> list[str]:
        user_name = record.get("user_name", None) or record.get(
            "playfab_id", "<UNKNOWN>"
        )
        kill_count = record.get("kill_count", 0)

        death_count = record.get("death_count", 0)

        ratio = str(round(kill_count / death_count, 2)) if death_count > 0 else "-"
        kill_count_txt = (
            human_format(kill_count)
            if kill_count >= bot_config.boards_min_to_format
            else kill_count
        )
        death_count_txt = (
            human_format(death_count)
            if death_count >= bot_config.boards_min_to_format
            else death_count
        )
        if len(user_name) > 26:
            user_name = user_name[:24] + ".."
        return [user_name, kill_count_txt, death_count_txt, ratio]

    async def update_achieved_ranks(self, records: dict):
        inf = float("inf")
        await update_achieved_ranks(
            [
                {"playfab_id": item["playfab_id"], "rank": index + 1}
                for (index, item) in enumerate(records)
                if item.get("achiev", {}).get("lifetime_rank", inf) < index + 1
            ],
            self._kills_collection,
        )

    async def send_board(self):
        top_20_items: list[dict] = (
            await self._kills_collection.find()
            .sort("kill_count", -1)
            .limit(20)
            .to_list()
        )
        asyncio.create_task(self.update_achieved_ranks(top_20_items))
        ascii_table = (
            "```"
            + t2a(
                header=["Rank", "Username", "K", "D", "R"],
                body=[
                    [index + 1, *self.compute_kdr(item)]
                    for (index, item) in enumerate(top_20_items)
                ],
            )
            + "```"
        )
        current_time = round(datetime.now(timezone.utc).timestamp())
        time_sig = f"Last updated: <t:{current_time}> (<t:{current_time}:R>)"
        embed = make_embed(
            ":skull: KILL RECORDS (top 20) :skull:",
            description=time_sig + "\n" + ascii_table,
            color=discord.Colour(15548997),
            footer_txt=f"Updates every {compute_time_txt(self._time_interval_mins)}",
        )
        if not self._current_message:
            self._current_message = await self._channel.send(embed=embed)
            asyncio.create_task(self.write_msg_id())
        else:
            await self._current_message.edit(embed=embed)
