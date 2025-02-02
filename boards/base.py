import asyncio
import aiofiles
from aiofiles import os as aos
import discord
from discord.ext import tasks
from reactivex import Observer
from abc import ABC, abstractmethod
from common import logger


class Board(Observer[discord.Client], ABC):
    _channel_id: int = 0
    _channel: discord.TextChannel | None = None
    _current_message: discord.Message | None = None
    _time_interval: int = 60
    _time_interval_mins: int = 1

    @property
    @abstractmethod
    def file_path(self) -> str:
        pass

    def __init__(self, channel_id: int, time_interval: int = 60):
        self._channel_id = channel_id
        self._time_interval = time_interval
        self._time_interval_mins = time_interval / 60
        self.job.change_interval(seconds=time_interval)
        super().__init__()

    def on_next(self, client: discord.Client):
        asyncio.create_task(self.start(client))

    async def load_channel(self, client: discord.Client):
        self._channel = await client.fetch_channel(self._channel_id)

    async def start(self, client: discord.Client):
        logger.info(
            f"{self.__class__.__name__}: Retrieving discord channel {self._channel_id}"
        )
        await self.load_channel(client)
        await self.delete_previous_message()
        self.job.cancel()
        self.job.start()

    async def write_msg_id(self):
        async with aiofiles.open(self.file_path, "w") as file:
            await file.write(str(self._current_message.id))

    async def destroy_msg_id(self):
        file_exists = await aos.path.exists(self.file_path)
        if not file_exists:
            return
        await aiofiles.os.remove(self.file_path)

    async def delete_previous_message(self) -> str | None:
        try:
            file_exists = await aos.path.exists(self.file_path)
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
            await aiofiles.os.remove(self.file_path)
        except Exception as e:
            logger.error(
                f"{self.__class__.__name__}: Error deleting existing board: {e}"
            )

    @abstractmethod
    async def send_board(self):
        pass

    @tasks.loop()
    async def job(self):
        await self.send_board()
