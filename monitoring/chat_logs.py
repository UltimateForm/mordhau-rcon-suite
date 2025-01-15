import asyncio
from reactivex import Observer, Observable
from common.models import ChatEvent
import discord


class ChatLogs(Observer[ChatEvent]):
    _dc_client: discord.Client = None
    _channel: discord.TextChannel | None = None
    _channel_id: int = 0

    def __init__(
        self, observable_dc_client: Observable[discord.Client], channel_id: int
    ):
        observable_dc_client.subscribe(
            lambda x: asyncio.create_task(self._on_discord_ready(x))
        )
        self._channel_id = channel_id
        super().__init__()

    async def _on_discord_ready(self, dc_client: discord.Client):
        self._dc_client = dc_client
        self._channel = await self._dc_client.fetch_channel(self._channel_id)

    async def send_chat_log(self, chat_event: ChatEvent):
        if self._channel is None:
            return
        escaped_user_name = discord.utils.escape_markdown(chat_event.user_name)
        escaped_msg = discord.utils.escape_markdown(chat_event.message)
        escaped_id = discord.utils.escape_markdown(chat_event.player_id)
        scribe_link = f"https://mordhau-scribe.com/player/{escaped_id}"
        msg = f"**{escaped_user_name}** ([{escaped_id}]({scribe_link})): ``\x00{escaped_msg}\x00``"
        # ^ not sure what happens if i send null bytes.... but hey i'm an adventurer
        await self._channel.send(msg,)

    def on_next(self, value: ChatEvent):
        asyncio.create_task(self.send_chat_log(value))
