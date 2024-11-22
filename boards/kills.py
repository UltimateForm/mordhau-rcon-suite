import asyncio
import os
import aiofiles
import discord
from discord.ext import tasks
from datetime import datetime, timezone
from motor.motor_asyncio import (
    AsyncIOMotorCollection,
)
from table2ascii import table2ascii as t2a
from common import logger

from common.compute import compute_time_txt

BOARD_REFRESH_TIME = int(os.environ.get("KILLS_REFRESH_TIME", 60))


# TODO: create base class for these boards, too much duplication
class KillsScoreboard(discord.Client):
    _channel_id: int = 0
    _channel: discord.TextChannel | None = None
    _current_message: discord.Message | None = None
    _kills_collection: AsyncIOMotorCollection | None
    file_path = "./persist/kills_msg_id"

    def __init__(
        self,
        channel_id: int,
        kills_collection: AsyncIOMotorCollection | NameError,
        intents: discord.Intents,
        **kwargs,
    ):
        self._channel_id = channel_id
        self._kills_collection = kills_collection
        super().__init__(intents=intents, **kwargs)

    async def on_ready(self):
        logger.info(f"Retrieving kills scoreboard channel {self._channel_id}")
        self._channel = await self.fetch_channel(self._channel_id)
        await self.delete_previous_message()
        self.job.start()

    async def write_msg_id(self):
        async with aiofiles.open(self.file_path, "w") as file:
            await file.write(str(self._current_message.id))

    async def delete_previous_message(self) -> str | None:
        try:
            file_exists = await aiofiles.os.path.exists(self.file_path)
            if not file_exists:
                return
            msg_id: str | None = ""
            async with aiofiles.open(self.file_path, "r") as file:
                msg_id = await file.read()
            if not msg_id.isdecimal():
                return
            parsed_msg_id = int(msg_id)
            msg = await self._channel.fetch_message(parsed_msg_id)
            await msg.delete()
        except Exception as e:
            logger.error(f"KillsScoreboard: Error deleting existing board: {e}")

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
            title=":skull: KILL RECORDS (top 20) :skull:",
            description=time_sig + "\n" + ascii_table,
            color=discord.Colour(15844367),
        )
        embed.set_footer(
            text=f"""
Updates every {compute_time_txt(BOARD_REFRESH_TIME/60)}
Bot source: https://github.com/UltimateForm/mordhau-rcon-suite
                """
        )
        if not self._current_message:
            self._current_message = await self._channel.send(embed=embed)
            asyncio.create_task(self.write_msg_id())
        else:
            await self._current_message.edit(embed=embed)

    @tasks.loop(seconds=BOARD_REFRESH_TIME)
    async def job(self):
        await self.send_board()
