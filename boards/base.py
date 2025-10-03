import aiofiles
from aiofiles import os as aos
import discord
from discord.ext import tasks, commands
from abc import abstractmethod
from common import logger
from common.gc_shield import backtask


class Board(commands.Cog):
    announcement: str = ""
    _channel_id: int = 0
    _channel: discord.abc.Messageable | None = None
    _current_message: discord.Message | None = None
    _time_interval: int = 60
    _time_interval_mins: float = 1
    _client: discord.Client

    @property
    @abstractmethod
    def file_path(self) -> str:
        pass

    def __init__(
        self, client: discord.Client, channel_id: int, time_interval: int | None = 60
    ):
        self._channel_id = channel_id
        self._client = client
        self._time_interval = time_interval or 60
        self._time_interval_mins = self._time_interval / 60
        self.job.change_interval(seconds=float(self._time_interval))
        super().__init__()

    @commands.Cog.listener()
    async def on_ready(self):
        backtask(self.start(self._client))

    async def load_channel(self, client: discord.Client):
        channel = await client.fetch_channel(self._channel_id)
        if isinstance(channel, discord.abc.Messageable):
            self._channel = channel
        else:
            logger.error(
                f"{self.__class__.__name__}: Channel {self._channel_id} is not a messageable channel"
            )

    async def start(self, client: discord.Client):
        logger.info(
            f"{self.__class__.__name__}: Retrieving discord channel {self._channel_id}"
        )
        await self.load_channel(client)
        await self.delete_previous_message()
        if self.job.is_running():
            self._current_message = None
            self.job.restart()
        else:
            self.job.start()

    async def write_msg_id(self):
        if not self._current_message:
            return
        async with aiofiles.open(self.file_path, "w") as file:
            await file.write(str(self._current_message.id))

    async def destroy_msg_id(self):
        file_exists = await aos.path.exists(self.file_path)
        if not file_exists:
            return
        await aos.remove(self.file_path)

    async def delete_previous_message(self):
        if not self._channel:
            return
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
            await aos.remove(self.file_path)
        except Exception as e:
            logger.error(
                f"{self.__class__.__name__}: Error deleting existing board: {e}"
            )

    @abstractmethod
    async def send_board(self):
        pass

    @tasks.loop()
    async def job(self):
        try:
            await self.send_board()
        except Exception as e:
            logger.error(f"{self.__class__.__name__}: Error sending board: {e}")
