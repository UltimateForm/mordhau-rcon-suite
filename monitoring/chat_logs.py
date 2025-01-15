import asyncio
from reactivex import Observer, Observable
from common.models import ChatEvent
import discord
from discord.ext.commands.bot import Bot
from discord.ext.commands.context import Context
from common.discord import make_embed
from rcon.rcon import RconContext
from common import logger


class ChatLogs(Observer[ChatEvent]):
    _dc_client: discord.Client = None
    _channel: discord.TextChannel | None = None
    _channel_id: int = 0
    _allowed_mentions: discord.AllowedMentions = None

    def __init__(
        self,
        observable_dc_client: Observable[discord.Client],
        channel_id: int,
        dc_bot: Bot,
    ):
        observable_dc_client.subscribe(
            lambda x: asyncio.create_task(self._on_discord_ready(x))
        )
        self._channel_id = channel_id
        self._allowed_mentions = discord.AllowedMentions(roles=True)
        self.create_say_command(dc_bot)
        super().__init__()

    def create_say_command(self, dc_bot: Bot):
        async def cmd(ctx: Context, *args: str):
            if ctx.channel.id != self._channel_id:
                return
            msg = " ".join(args)
            author = ctx.author.display_name
            try:
                async with RconContext() as client:
                    r = await client.execute(f"say {author} > {msg}")
                    logger.info(
                        f"{self.__class__.__name__}: {ctx.command} '{msg}': RESPONSE {r}"
                    )
                await ctx.message.add_reaction("👌")
            except Exception as e:
                embed = make_embed(ctx.command, color=discord.Colour(15548997))
                embed.add_field(name="Success", value=False, inline=False)
                embed.add_field(name="Error", value=str(e), inline=False)
                await ctx.message.reply(embed=embed)

        dc_bot.command(
            "say",
        )(cmd)

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
        if "@admin" in escaped_msg:
            msg += " @here"
        await self._channel.send(msg)

    def on_next(self, value: ChatEvent):
        asyncio.create_task(self.send_chat_log(value))
