import seasons.season_controller as sc
import discord
from discord.ext import commands
from common.discord import make_embed as common_make_embed, make_season_embed
from config_client.models import BotConfig, SeasonConfig, EmbedConfig
import json
from dacite import from_dict
from datetime import date
from dataclasses import fields
import re


def to_json(json_str: str) -> SeasonConfig:
    return from_dict(SeasonConfig, json.loads(json_str))


def make_embed(ctx: commands.Context):
    embed = common_make_embed(ctx.command, color=discord.Colour(1752220))
    return embed


def register_season_cfg_commands(bot: commands.Bot, bot_config: BotConfig):
    bot_channel = bot_config.config_bot_channel

    async def info(ctx: commands.Context):
        if bot_channel and ctx.channel.id != bot_channel:
            return
        embed = make_embed(ctx)

        try:
            exists = await SeasonConfig.aexists()
            if not exists:
                raise FileNotFoundError(
                    "No season is currently available, you can create one with `.season:create <type[both|kdr|playtime]> <name>`"
                )
            season = await SeasonConfig.aload()
            embed.add_field(name="Name", value=season.name)
            embed.add_field(name="Creation date", value=season.created_date)
            embed.add_field(name="Active", value=season.is_active)
            embed.add_field(name="Channel", value=season.channel)
            exclude_players_txt = (
                "\n".join(season.exclude) if season.exclude else "None"
            )
            embed.add_field(
                name="Exclude players",
                value="```\n" + exclude_players_txt + "\n```",
                inline=False,
            )
        except Exception as e:
            embed.add_field(name="Success", value=False, inline=False)
            embed.add_field(name="Error", value=str(e), inline=False)
            embed.color = 15548997  # red
        await ctx.message.reply(embed=embed)

    bot.command("season:info")(info)

    async def create(ctx: commands.Context, season_type: str, name: str):
        if bot_channel and ctx.channel.id != bot_channel:
            return
        try:
            exists = await SeasonConfig.aexists()
            if exists:
                raise FileNotFoundError(
                    "A season already exists, delete current one with `.season:delete` before creating new one"
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
            await ctx.reply("Season created")
        except Exception as e:
            embed = make_embed(ctx)
            embed.add_field(name="Success", value=False, inline=False)
            embed.add_field(name="Error", value=str(e), inline=False)
            embed.color = 15548997  # red
            await ctx.message.reply(embed=embed)

    bot.command("season:create")(create)

    async def delete(ctx: commands.Context):
        if bot_channel and ctx.channel.id != bot_channel:
            return
        try:
            exists = await SeasonConfig.aexists()
            if not exists:
                raise ValueError("No season is currently available")
            current = await SeasonConfig.aload()
            if current.is_active:
                raise ValueError(
                    "Season is active, end it before deleting (`.season:end`)"
                )
            await SeasonConfig.adelete()
            sc.SEASON_TOPIC.on_next(sc.SeasonEvent.DESTROY)
            await ctx.reply("Deleted")
        except Exception as e:
            embed = make_embed(ctx)
            embed.add_field(name="Success", value=False, inline=False)
            embed.add_field(name="Error", value=str(e), inline=False)
            embed.color = 15548997  # red
            await ctx.message.reply(embed=embed)

    bot.command("season:delete")(delete)

    async def channel_id(ctx: commands.Context, channel: int):
        if bot_channel and ctx.channel.id != bot_channel:
            return
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
            embed = make_embed(ctx)
            embed.add_field(name="Success", value=False, inline=False)
            embed.add_field(name="Error", value=str(e), inline=False)
            embed.color = 15548997  # red
            await ctx.message.reply(embed=embed)

    bot.command("season:channel")(channel_id)

    async def exclude(ctx: commands.Context, *playfab_ids: str):
        if bot_channel and ctx.channel.id != bot_channel:
            return
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
            embed = make_embed(ctx)
            embed.add_field(name="Success", value=False, inline=False)
            embed.add_field(name="Error", value=str(e), inline=False)
            embed.color = 15548997  # red
            await ctx.message.reply(embed=embed)

    bot.command("season:exclude")(exclude)

    async def start(ctx: commands.Context):
        if bot_channel and ctx.channel.id != bot_channel:
            return
        try:
            exists = await SeasonConfig.aexists()
            if not exists:
                raise ValueError(
                    "No season is currently available, you can create one with `.season:create <type[both|kdr|playtime]> <name>`"
                )
            season = await SeasonConfig.aload()
            if season.is_active:
                raise ValueError("Season has already started")
            if not season.channel:
                raise ValueError(
                    "Season has no registered channel id, run `.season:channel <channelId>` to set the channel"
                )
            season.start_date = date.today().strftime("%d/%m/%Y")
            await season.asave()
            sc.SEASON_TOPIC.on_next(sc.SeasonEvent.START)
            await ctx.reply(":saluting_face:")
        except Exception as e:
            embed = make_embed(ctx)
            embed.add_field(name="Success", value=False, inline=False)
            embed.add_field(name="Error", value=str(e), inline=False)
            embed.color = 15548997  # red
            await ctx.message.reply(embed=embed)

    bot.command("season:start")(start)

    async def end(ctx: commands.Context):
        if bot_channel and ctx.channel.id != bot_channel:
            return
        try:
            exists = await SeasonConfig.aexists()
            if not exists:
                raise ValueError("No season is currently available")
            season = await SeasonConfig.aload()
            if not season.is_active:
                raise ValueError(
                    "Season isn't active. Run .season:start to start season"
                )
            season.end_date = date.today().strftime("%d/%m/%Y")
            await season.asave()
            sc.SEASON_TOPIC.on_next(sc.SeasonEvent.END)
            await ctx.reply(":saluting_face:")
        except Exception as e:
            embed = make_embed(ctx)
            embed.add_field(name="Success", value=False, inline=False)
            embed.add_field(name="Error", value=str(e), inline=False)
            embed.color = 15548997  # red
            await ctx.message.reply(embed=embed)

    bot.command("season:end")(end)

    async def set_embed(ctx: commands.Context, field: str, value: str):
        if bot_channel and ctx.channel.id != bot_channel:
            return
        embed = make_embed(ctx)
        try:
            allowed_fields = [f.name for f in fields(EmbedConfig)]
            if field not in allowed_fields:
                raise ValueError(f"Invalid field. Allowed fields: {allowed_fields}")
            exists = await SeasonConfig.aexists()
            if not exists:
                raise ValueError("No season is currently available")
            season = await SeasonConfig.aload()
            setattr(season.embed_config, field, value)
            await season.asave()
            await ctx.reply("Updated")
            s_embed = make_season_embed(season)
            s_embed.description = (
                s_embed.description + "\n```PLAYERS TABLE WILL BE HERE```"
            )
            await ctx.reply(embed=s_embed)
            sc.SEASON_TOPIC.on_next(sc.SeasonEvent.UPDATE)
        except Exception as e:
            embed = make_embed(ctx)
            embed.add_field(name="Success", value=False, inline=False)
            embed.add_field(name="Error", value=str(e), inline=False)
            embed.color = 15548997  # red
            await ctx.message.reply(embed=embed)

    bot.command("season:embed")(set_embed)
