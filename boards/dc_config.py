from discord.ext import commands
from boards.base import Board
from boards.info import InfoBoard
from boards.kills import KillsScoreboard
from boards.playtime import PlayTimeScoreboard
from config_client.models import BotConfig
from common.discord import (
    BotHelper,
    bot_config_channel_checker,
    make_embed as common_make_embed,
)
import discord

KNOWN_BOARDS = [
    InfoBoard.__name__,
    KillsScoreboard.__name__,
    PlayTimeScoreboard.__name__,
]
KNOWN_BOARDS_JOINED = ", ".join(KNOWN_BOARDS)


class BoardCommands(commands.Cog):
    _client: commands.Bot
    _cfg: BotConfig

    def __init__(self, client: commands.Bot, bot_config: BotConfig) -> None:
        self._client = client
        self._cfg = bot_config
        self.boards.add_check(bot_config_channel_checker(bot_config))
        super().__init__()

    def make_embed(self, ctx: commands.Context):
        embed = common_make_embed(str(ctx.command), color=discord.Colour(9807270))
        return embed

    def get_board_cog(self, name: str) -> Board:

        if name not in KNOWN_BOARDS:
            raise ValueError(
                f"{name} is not a known board. The known ones are {KNOWN_BOARDS_JOINED}."
            )
        else:
            cog = self._client.get_cog(name)
            if isinstance(cog, Board):
                return cog
            else:
                raise ValueError("Could not find board instance")

    @commands.group(invoke_without_command=False, description="Boards admin commands")
    async def boards(self, ctx: commands.Context):
        if ctx.subcommand_passed is None:
            helper = self._client.get_cog("BotHelper")
            if not isinstance(helper, BotHelper) or not ctx.command:
                return
            await helper.help(ctx, ctx.command.name)

    @boards.command(
        description=f"set an announcement to be shown in a sent board, identify the boards by the names {KNOWN_BOARDS_JOINED}",
        usage="<board_name> <announcement>",
    )
    async def announce(self, ctx: commands.Context, board_name: str, *announce: str):
        if (
            self._cfg.config_bot_channel
            and ctx.channel.id != self._cfg.config_bot_channel
        ):
            return
        embed = self.make_embed(ctx)
        try:
            board = self.get_board_cog(board_name)
            board.announcement = " ".join(announce)
            embed.add_field(name="Success", value=str(True))
            await ctx.reply(embed=embed)
        except Exception as e:
            embed.add_field(name="Success", value=str(False), inline=False)
            embed.add_field(name="Error", value=str(e), inline=False)
            embed.color = 15548997  # red
            await ctx.message.reply(embed=embed)

    @boards.command(
        description=f"resets a board, will delete current board message and send a new one, identify the boards by the names {KNOWN_BOARDS_JOINED}",
        usage="<board_name>",
    )
    async def reset(self, ctx: commands.Context, board_name: str):
        if (
            self._cfg.config_bot_channel
            and ctx.channel.id != self._cfg.config_bot_channel
        ):
            return
        embed = self.make_embed(ctx)
        try:
            board = self.get_board_cog(board_name)
            await board.start(board._client)
            embed.add_field(name="Success", value=str(True))
            await ctx.reply(embed=embed)
        except Exception as e:
            embed.add_field(name="Success", value=str(False), inline=False)
            embed.add_field(name="Error", value=str(e), inline=False)
            embed.color = 15548997  # red
            await ctx.message.reply(embed=embed)
