import asyncio
import discord
from datetime import datetime, timezone
from motor.motor_asyncio import (
    AsyncIOMotorCollection,
)
from table2ascii import table2ascii as t2a
from boards.base import Board

from common.compute import compute_time_txt
from common.discord import make_embed


class PlayTimeScoreboard(Board):
    _playtime_collection: AsyncIOMotorCollection

    @property
    def file_path(self) -> str:
        return "./persist/playtime_msg_id"

    def __init__(
        self,
        playtime_collection: AsyncIOMotorCollection,
        channel_id,
        time_interval: int | None = 60,
    ):
        self._playtime_collection = playtime_collection
        super().__init__(channel_id, time_interval)

    async def send_board(self):
        if not self._channel:
            raise ValueError(
                "{self.__class__.__name__}: Channel {self._channel_id} not loaded"
            )
        top_20_items: list[dict] = (
            await self._playtime_collection.find()
            .sort("minutes", -1)
            .limit(20)
            .to_list()
        )
        ascii_table = (
            "```"
            + t2a(
                header=["Rank", "Username", "Time"],
                body=[
                    [
                        index + 1,
                        item.get("user_name", None)
                        or item.get("playfab_id", "<UNKNOWN>"),
                        compute_time_txt(item["minutes"]),
                    ]
                    for (index, item) in enumerate(top_20_items)
                ],
            )
            + "```"
        )
        current_time = round(datetime.now(timezone.utc).timestamp())
        time_sig = f"Last updated: <t:{current_time}> (<t:{current_time}:R>)"
        embed = make_embed(
            ":clock4: PLAYTIME RECORDS (top 20) :clock4:",
            description=time_sig + "\n" + ascii_table,
            color=discord.Colour(5763719),
            footer_txt=f"Updates every {compute_time_txt(self._time_interval_mins)}\nUnknown players will be shown by playfab id only, login and logout to capture username",
        )
        if not self._current_message:
            self._current_message = await self._channel.send(embed=embed)
            asyncio.create_task(self.write_msg_id())
        else:
            await self._current_message.edit(embed=embed)
