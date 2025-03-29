import seasons.season_controller as sc
import discord
from discord.ext import commands
from common.discord import (
    BotHelper,
    bot_config_channel_checker,
    make_embed as common_make_embed,
    make_season_embed,
)
from config_client.models import BotConfig, SeasonConfig, EmbedConfig
import json
from dacite import from_dict
from datetime import date
from dataclasses import fields
import re


def to_json(json_str: str) -> SeasonConfig:
    return from_dict(SeasonConfig, json.loads(json_str))


ALLOWED_EMBED_FIELDS = [f.name for f in fields(EmbedConfig)]
ALLOWED_EMBED_FIELDS_STR = ", ".join(ALLOWED_EMBED_FIELDS)


class SeasonAdminCommands(commands.Cog):
    _client: commands.Bot
    _cfg: BotConfig

    def __init__(self, client: commands.Bot, bot_config: BotConfig) -> None:
        self._client = client
        self._cfg = bot_config
        self.season.add_check(bot_config_channel_checker(bot_config))
        super().__init__()

    def make_embed(self, ctx: commands.Context):
        embed = common_make_embed(str(ctx.command), color=discord.Colour(1752220))
        return embed

    @commands.group(invoke_without_command=False, description="Season admin commands")
    async def season(self, ctx: commands.Context):
        if ctx.subcommand_passed is None:
            helper = self._client.get_cog("BotHelper")
            if not isinstance(helper, BotHelper) or not ctx.command:
                return
            await helper.help(ctx, ctx.command.name)

    @season.command(description="get info about current configured season")
    async def info(self, ctx: commands.Context):
        embed = self.make_embed(ctx)

        try:
            exists = await SeasonConfig.aexists()
            if not exists:
                raise FileNotFoundError(
                    "No season is currently available, you can create one with `.season create`"
                )
            season = await SeasonConfig.aload()
            embed.add_field(name="Name", value=season.name)
            embed.add_field(name="Creation date", value=season.created_date)
            embed.add_field(name="Active", value=str(season.is_active))
            embed.add_field(name="Channel", value=str(season.channel))
            exclude_players_txt = (
                "\n".join(season.exclude) if season.exclude else "None"
            )
            embed.add_field(
                name="Exclude players",
                value="```\n" + exclude_players_txt + "\n```",
                inline=False,
            )
        except Exception as e:
            embed.add_field(name="Success", value=str(False), inline=False)
            embed.add_field(name="Error", value=str(e), inline=False)
            embed.color = 15548997  # red
        await ctx.message.reply(embed=embed)

    @season.command(
        description="create season, currently only supported season_type is `kdr`, name should not have spaces ",
        usage="<season_type> <name>",
        help="kdr Winter2022",
    )
    async def create(self, ctx: commands.Context, season_type: str, name: str):
        try:
            exists = await SeasonConfig.aexists()
            if exists:
                raise FileExistsError(
                    "A season already exists, delete current one with `.season delete` before creating new one"
                )
            name_pattern = re.compile(r"^\S*$")
            if not name_pattern.match(name):
                raise ValueError("Name must not have spaces in name")
            season = SeasonConfig(
                name,
                [],
                season_type,
            )
            await season.asave()
            sc.SEASON_TOPIC.on_next(sc.SeasonEvent.CREATE)
            await ctx.reply(f"Season {name} created")
        except Exception as e:
            embed = self.make_embed(ctx)
            embed.add_field(name="Success", value=str(False), inline=False)
            embed.add_field(name="Error", value=str(e), inline=False)
            embed.color = 15548997  # red
            await ctx.message.reply(embed=embed)

    @season.command(description="delete configured season")
    async def delete(self, ctx: commands.Context):
        try:
            exists = await SeasonConfig.aexists()
            if not exists:
                raise ValueError("No season is currently available")
            current = await SeasonConfig.aload()
            if current.is_active:
                raise ValueError(
                    "Season is active, end it before deleting (`.season end`)"
                )
            await SeasonConfig.adelete()
            sc.SEASON_TOPIC.on_next(sc.SeasonEvent.DESTROY)
            await ctx.reply("Deleted")
        except Exception as e:
            embed = self.make_embed(ctx)
            embed.add_field(name="Success", value=str(False), inline=False)
            embed.add_field(name="Error", value=str(e), inline=False)
            embed.color = 15548997  # red
            await ctx.message.reply(embed=embed)

    @season.command(
        description="set channel (by id) to send season score board",
        usage="<channel_id>",
        help="2912891271860",
    )
    async def channel(self, ctx: commands.Context, channel: int):
        try:
            exists = await SeasonConfig.aexists()
            if not exists:
                raise ValueError("No season is currently available")
            season = await SeasonConfig.aload()
            season.channel = channel
            await season.asave()
            sc.SEASON_TOPIC.on_next(sc.SeasonEvent.UPDATE)
            await ctx.reply("Updated")
        except Exception as e:
            embed = self.make_embed(ctx)
            embed.add_field(name="Success", value=str(False), inline=False)
            embed.add_field(name="Error", value=str(e), inline=False)
            embed.color = 15548997  # red
            await ctx.message.reply(embed=embed)

    @season.command(
        description="exclude players from season, will not remove already accounted score",
        usage="<playfab_id_1> <playfab_id_2> <playfab_id_3> <...etc>",
        help="BB50E7E5B75300F6 AB07435720F6A3",
    )
    async def exclude(self, ctx: commands.Context, *playfab_ids: str):
        try:
            exists = await SeasonConfig.aexists()
            if not exists:
                raise ValueError("No season is currently available")
            season = await SeasonConfig.aload()
            season.exclude.extend(playfab_ids)
            await season.asave()
            sc.SEASON_TOPIC.on_next(sc.SeasonEvent.UPDATE)
            await ctx.reply(f"Added {playfab_ids} to {season.name} excluded players")
        except Exception as e:
            embed = self.make_embed(ctx)
            embed.add_field(name="Success", value=str(False), inline=False)
            embed.add_field(name="Error", value=str(e), inline=False)
            embed.color = 15548997  # red
            await ctx.message.reply(embed=embed)

    @season.command(
        description="include players in season",
        usage="<playfab_id_1> <playfab_id_2> <playfab_id_3> <...etc>",
        help="BB50E7E5B75300F6 AB07435720F6A3",
    )
    async def include(self, ctx: commands.Context, *playfab_ids: str):
        try:
            exists = await SeasonConfig.aexists()
            if not exists:
                raise ValueError("No season is currently available")
            season = await SeasonConfig.aload()
            for playfab_id in playfab_ids:
                if playfab_id in season.exclude:
                    season.exclude.remove(playfab_id)
            await season.asave()
            sc.SEASON_TOPIC.on_next(sc.SeasonEvent.UPDATE)
            await ctx.reply(
                f"Removed {playfab_ids} from {season.name} excluded players"
            )
        except Exception as e:
            embed = self.make_embed(ctx)
            embed.add_field(name="Success", value=str(False), inline=False)
            embed.add_field(name="Error", value=str(e), inline=False)
            embed.color = 15548997  # red
            await ctx.message.reply(embed=embed)

    @season.command(
        description="start configured season, will error out if not ready to start"
    )
    async def start(self, ctx: commands.Context):
        try:
            exists = await SeasonConfig.aexists()
            if not exists:
                raise ValueError(
                    "No season is currently available, you can create one with `.season create`"
                )
            season = await SeasonConfig.aload()
            if season.is_active:
                raise ValueError("Season has already started")
            if season.end_date:
                raise ValueError(
                    "Season has already ended and cannot be restarted. Delete it (.season delete) and create a new one"
                )
            if not season.channel:
                raise ValueError(
                    "Season has no registered channel id, run `.season channel` to set the channel"
                )
            season.start_date = date.today().strftime("%d/%m/%Y")
            await season.asave()
            sc.SEASON_TOPIC.on_next(sc.SeasonEvent.START)
            await ctx.reply(":saluting_face:")
        except Exception as e:
            embed = self.make_embed(ctx)
            embed.add_field(name="Success", value=str(False), inline=False)
            embed.add_field(name="Error", value=str(e), inline=False)
            embed.color = 15548997  # red
            await ctx.message.reply(embed=embed)

    @season.command(description="end configured season")
    async def end(self, ctx: commands.Context):
        try:
            exists = await SeasonConfig.aexists()
            if not exists:
                raise ValueError("No season is currently available")
            season = await SeasonConfig.aload()
            if not season.is_active:
                raise ValueError(
                    "Season isn't active. Run `.season start` to start season"
                )
            season.end_date = date.today().strftime("%d/%m/%Y")
            await season.asave()
            sc.SEASON_TOPIC.on_next(sc.SeasonEvent.END)
            await ctx.reply(":saluting_face:")
        except Exception as e:
            embed = self.make_embed(ctx)
            embed.add_field(name="Success", value=str(False), inline=False)
            embed.add_field(name="Error", value=str(e), inline=False)
            embed.color = 15548997  # red
            await ctx.message.reply(embed=embed)

    @season.command(
        name="embed",
        description=f"customize embed fields, the allowed fields are {ALLOWED_EMBED_FIELDS_STR}",
        usage="<field> <value>",
        help='title "Winter 2022!"',
    )
    async def set_embed(self, ctx: commands.Context, field: str, *value: str):
        embed = self.make_embed(ctx)
        try:
            if field not in ALLOWED_EMBED_FIELDS:
                raise ValueError(
                    f"Invalid field. Allowed fields: {ALLOWED_EMBED_FIELDS}"
                )
            exists = await SeasonConfig.aexists()
            if not exists:
                raise ValueError("No season is currently available")
            season = await SeasonConfig.aload()
            setattr(season.embed_config, field, " ".join(value))
            await season.asave()
            await ctx.reply("Updated")
            s_embed = make_season_embed(season)
            players_table_example = "```PLAYERS TABLE WILL BE HERE```"
            s_embed.description = (
                s_embed.description + "\n" + players_table_example
                if s_embed.description
                else players_table_example
            )
            await ctx.reply(embed=s_embed)
            sc.SEASON_TOPIC.on_next(sc.SeasonEvent.UPDATE)
        except Exception as e:
            embed = self.make_embed(ctx)
            embed.add_field(name="Success", value=str(False), inline=False)
            embed.add_field(name="Error", value=str(e), inline=False)
            embed.color = 15548997  # red
            await ctx.message.reply(embed=embed)
