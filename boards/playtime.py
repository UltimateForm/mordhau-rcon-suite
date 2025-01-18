import asyncio
import discord
from boards.base import Board
from datetime import datetime, timezone
from motor.motor_asyncio import (
    AsyncIOMotorCollection,
)
from table2ascii import table2ascii as t2a

from common.compute import compute_time_txt


class PlayTimeScoreboard(Board):
    _playtime_collection: AsyncIOMotorCollection | None

    @property
    def file_path(self) -> str:
        return "./persist/playtime_msg_id"

    def __init__(
        self, playtime_collection: AsyncIOMotorCollection, channel_id, time_interval=60
    ):
        self._playtime_collection = playtime_collection
        super().__init__(channel_id, time_interval)

    async def send_board(self):
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
        embed = discord.Embed(
            title="<:ClockofDestiny:1310130670798110810> PLAYTIME LEADERBOARD (TOP 20) <:ClockofDestiny:1310130670798110810>",
            description=time_sig + "\n" + ascii_table,
            color=discord.Colour(int("1eff00", 16)),
        )
        embed.set_footer(
            text=f"""
Updates every {compute_time_txt(self._time_interval_mins)}
Data has been collecting since 5/25/2024
                """
        )
        if not self._current_message:
            self._current_message = await self._channel.send(embed=embed)
            asyncio.create_task(self.write_msg_id())
        else:
            await self._current_message.edit(embed=embed)
