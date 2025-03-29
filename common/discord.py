import asyncio
from typing import Iterable
from discord.ext import commands
import discord
from reactivex import Subject
from config_client.data import bot_config
from config_client.models import SeasonConfig
from datetime import datetime, timezone
from config_client.models import BotConfig

common_intents = discord.Intents.default()
common_intents.message_content = True


def channel_checker(channel_id: int):
    def check(ctx: commands.Context):
        if not channel_id or ctx.channel.id != channel_id:
            return False
        return True

    return check


def bot_config_channel_checker(config: BotConfig):
    return channel_checker(config.config_bot_channel)


def make_embed(
    title: str,
    description: str | None = None,
    color: discord.Colour | None = None,
    footer_txt: str | None = None,
):

    footer_txt_env = (
        bot_config.embed_footer_txt
        or "Bot source: https://github.com/UltimateForm/mordhau-rcon-suite"
    )
    footer_icon = bot_config.embed_footer_icon
    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_footer(
        text="\n".join([footer_txt, footer_txt_env]) if footer_txt else footer_txt_env,
        icon_url=footer_icon,
    )
    return embed


def make_season_embed(season_config: SeasonConfig):
    current_time = round(datetime.now(timezone.utc).timestamp())
    description = f"Last updated: <t:{current_time}> (<t:{current_time}:R>)"
    if season_config.embed_config.description:
        description = season_config.embed_config.description + "\n" + description
    embed = make_embed(
        title=season_config.embed_config.title or season_config.name,
        description=description,
        footer_txt=season_config.embed_config.footer_txt or None,
    )
    embed.color = 15844367
    if season_config.embed_config.image_url:
        embed.set_image(url=season_config.embed_config.image_url)
    return embed


class ObservableDiscordClient(discord.Client, Subject[discord.Client]):
    def __init__(self, intents: discord.Intents, loop: asyncio.AbstractEventLoop):
        discord.Client.__init__(self, intents=intents, loop=loop)
        Subject.__init__(self)

    async def on_ready(self):
        self.on_next(self)
        self.on_completed()


class BotHelper(commands.Cog):
    _client: commands.Bot
    _cfg: BotConfig

    def __init__(self, client: commands.Bot, bot_config: BotConfig):
        self._client = client
        self._cfg = bot_config
        self.help

    def get_commands_help(
        self, ctx: commands.Context, cmds: Iterable[commands.Command], padding=""
    ):
        cmds_lines: list[str] = []
        for cmd in cmds:
            if len(cmd.checks):
                check_pass = any(checker(ctx) for checker in cmd.checks)  # type: ignore
                if not check_pass:
                    continue
            cmd_head = f"- **{cmd.name}**"
            if cmd.description:
                cmd_head += f": {cmd.description}"
            cmds_lines.append(cmd_head)
            cmd_parents = [parent.name for parent in cmd.parents]
            cmd_call = " ".join([*cmd_parents, cmd.name])

            if cmd.usage:
                cmds_lines.append(
                    f"  - usage: `{self._client.command_prefix}{cmd_call} {cmd.usage}`"
                )
            if cmd.help:
                cmds_lines.append(
                    f"  - example: `{self._client.command_prefix}{cmd_call} {cmd.help}`"
                )
        return list(map(lambda x: padding + x, cmds_lines))

    def get_group_help(
        self, ctx: commands.Context, group: commands.Group, padding="  "
    ):
        group_help: list[str] = [padding + "- commands"]
        inner_padding = padding + padding
        group_help.extend(self.get_commands_help(ctx, group.commands, inner_padding))
        return group_help

    @commands.command(
        description="get help about a command, or use without any command to get help about all commands",
        usage="<optional_command>",
    )
    async def help(self, ctx: commands.Context, target: str | None):
        cmds: Iterable[commands.Command] = []
        cmds_lines: list[str] = []
        if target:
            cmd = next(
                (cmd for cmd in self._client.commands if cmd.name == target), None
            )
            if not cmd:
                await ctx.reply(f"{target} is not a known command or command group")
                return
            if len(cmd.checks):
                check_pass = any(checker(ctx) for checker in cmd.checks)  # type: ignore
                if not check_pass:
                    await ctx.reply(f"{target} is not a known command or command group")
                    return
            if isinstance(cmd, commands.Group):
                cmds = list(cmd.commands)
            else:
                cmds = [cmd]
        else:
            cmds_lines.append("## Mordhau Rcon Suite")
            cmds = self._client.commands
        cmds_lines.extend(self.get_commands_help(ctx, cmds))
        if not target:
            cmds_lines.append(
                "\nSource code https://github.com/UltimateForm/mordhau-rcon-suite"
            )
        await ctx.reply(content="\n".join(cmds_lines), suppress=True)
