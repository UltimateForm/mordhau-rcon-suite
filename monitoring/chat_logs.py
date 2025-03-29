import asyncio
from reactivex import Observer, Observable
from common.models import ChatEvent
import discord
from discord.ext.commands.bot import Bot
from common.discord import channel_checker, make_embed
from config_client.models import BotConfig
from rcon.rcon import RconContext
from common import logger
from discord.ext import commands


class ChatLogs(Observer[ChatEvent | None]):
    _dc_client: discord.Client
    _channel: discord.abc.Messageable | None = None
    _channel_id: int = 0
    _allowed_mentions: discord.AllowedMentions

    def __init__(
        self,
        observable_dc_client: Observable[discord.Client],
        bot_config: BotConfig,
        dc_bot: Bot,
    ):
        if not bot_config.chat_logs_channel:
            raise ValueError(
                "ChatLogs instantiated without actual channel to send logs to"
            )

        def launch_discord_ready(x: discord.Client):
            asyncio.create_task(self._on_discord_ready(x))

        observable_dc_client.subscribe(launch_discord_ready)
        self._channel_id = bot_config.chat_logs_channel
        self._allowed_mentions = discord.AllowedMentions(roles=True)
        say_cmd = dc_bot.command(
            name="say",
            description="send message to ingame chat",
            usage="<message>",
            help="ay yo, it's ya boi from discord comming at you with a new message",
        )(self.say)
        say_cmd.add_check(channel_checker(self._channel_id))
        super().__init__()

    async def say(self, ctx: commands.Context, *args: str):
        msg = " ".join(args)
        author = ctx.author.display_name
        try:
            logger.info(f"{self.__class__.__name__}: {ctx.command} '{msg}'")
            async with RconContext() as client:
                r = await client.execute(f"say {author} > {msg}")
                logger.info(f"{self.__class__.__name__}: {r}")
            await ctx.message.add_reaction("👌")
        except Exception as e:
            embed = make_embed(str(ctx.command), color=discord.Colour(15548997))
            embed.add_field(name="Success", value=str(False), inline=False)
            embed.add_field(name="Error", value=str(e), inline=False)
            await ctx.message.reply(embed=embed)

    async def _on_discord_ready(self, dc_client: discord.Client):
        self._dc_client = dc_client
        channel = await self._dc_client.fetch_channel(self._channel_id)
        if isinstance(channel, discord.abc.Messageable):
            self._channel = channel

    async def send_chat_log(self, chat_event: ChatEvent):
        if self._channel is None or chat_event is None:
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
