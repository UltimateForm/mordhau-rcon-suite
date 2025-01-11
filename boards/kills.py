import asyncio
import discord
from datetime import datetime, timezone
from motor.motor_asyncio import (
    AsyncIOMotorCollection,
)
from table2ascii import table2ascii as t2a
from boards.base import Board
from config_client.data import bot_config
from common.compute import compute_time_txt

BOARD_REFRESH_TIME = bot_config.kills_refresh_time or 60


class KillsScoreboard(Board):
    _kills_collection: AsyncIOMotorCollection | None

    @property
    def file_path(self) -> str:
        return "./persist/kills_msg_id"

    def __init__(
        self, kills_collection: AsyncIOMotorCollection, channel_id, time_interval=60
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
        if len(user_name) > 26:
            user_name = user_name[:24] + ".."
        return [user_name, kill_count, death_count, ratio]

    async def send_board(self):
        top_20_items: list[dict] = (
            await self._kills_collection.find()
            .sort("kill_count", -1)
            .limit(20)
            .to_list()
        )
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
        embed = discord.Embed(
            title="<:ape_skull:1310131648234262538> KILL LEADERBOARD (TOP 20) <:death_among_us:1310131176228519976>",
            description=time_sig + "\n" + ascii_table,
            color=discord.Colour(int("ff0000", 16)),
        )
        embed.set_footer(
            text=f"""
Updates every {compute_time_txt(self._time_interval_mins)}
Data has been collecting since 11/20/2024
                """
        )
        if not self._current_message:
            self._current_message = await self._channel.send(embed=embed)
            asyncio.create_task(self.write_msg_id())
        else:
            await self._current_message.edit(embed=embed)
