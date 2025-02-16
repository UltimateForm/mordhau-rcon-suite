import json
import discord
from discord.ext import commands
from common.discord import make_embed as common_make_embed
from config_client.data import pt_config, bot_config


def make_embed(ctx: commands.Context):
    embed = common_make_embed(str(ctx.command), color=discord.Colour(3447003))
    return embed


def register_cfg_dc_commands(bot: commands.Bot):
    @bot.command()
    async def ping(ctx: commands.Context):
        await ctx.message.reply(":ping_pong:")

    # TODO: jesus organize commands better after things calm down
    # TODO: create custom decorator so we dont have to repeat error handling in all the below commands

    bot_channel = bot_config.config_bot_channel

    async def set_tag_format(ctx: commands.Context, arg_format: str):
        if bot_channel and ctx.channel.id != bot_channel:
            return
        embed = make_embed(ctx)
        embed.add_field(name="ArgFormat", value=arg_format)
        try:
            if "{0}" not in arg_format:
                raise ValueError(
                    f"`{arg_format}` is not a valid format. Must include tag placeholder (`{{0}}`) in the format string."
                )
            pt_config.tag_format = arg_format
            pt_config.save()
            embed.add_field(name="Success", value=True, inline=False)
        except Exception as e:
            embed.add_field(name="Success", value=False, inline=False)
            embed.add_field(name="Error", value=str(e), inline=False)
            embed.color = 15548997  # red
        await ctx.message.reply(embed=embed)

    bot.command("setTagFormat")(set_tag_format)

    async def set_salute_timer(ctx: commands.Context, arg_timer: int):
        if bot_channel and ctx.channel.id != bot_channel:
            return
        embed = make_embed(ctx)
        embed.add_field(name="ArgFormat", value=f"{arg_timer} seconds")
        try:
            pt_config.salute_timer = arg_timer
            pt_config.save()
            embed.add_field(name="Success", value=True, inline=False)
        except Exception as e:
            embed.add_field(name="Success", value=False, inline=False)
            embed.add_field(name="Error", value=str(e), inline=False)
            embed.color = 15548997  # red
        await ctx.message.reply(embed=embed)

    bot.command("setSaluteTimer")(set_salute_timer)

    async def add_tag(ctx: commands.Context, arg_playfab_id: str, arg_tag: str):
        if bot_channel and ctx.channel.id != bot_channel:
            return
        embed = make_embed(ctx)
        embed.add_field(name="PlayfabId", value=arg_playfab_id)
        embed.add_field(name="Tag", value=arg_tag)
        try:
            pt_config.tags[arg_playfab_id] = arg_tag
            pt_config.save()
            embed.add_field(name="Success", value=True, inline=False)
        except Exception as e:
            embed.add_field(name="Success", value=False, inline=False)
            embed.add_field(name="Error", value=str(e), inline=False)
            embed.color = 15548997  # red
        await ctx.message.reply(embed=embed)

    bot.command("addTag")(add_tag)

    async def add_rename(ctx: commands.Context, arg_playfab_id: str, arg_rename: str):
        if bot_channel and ctx.channel.id != bot_channel:
            return
        embed = make_embed(ctx)
        embed.add_field(name="PlayfabId", value=arg_playfab_id)
        embed.add_field(name="Rename", value=arg_rename)
        try:
            if not pt_config:
                raise Exception(
                    "PersistentTitles config is not available, please verify logs for errors"
                )
            rename_cfg = pt_config.rename or {}
            rename_cfg[arg_playfab_id] = arg_rename
            if not pt_config.rename:
                pt_config.rename = rename_cfg
            pt_config.save()
            embed.add_field(name="Success", value=True, inline=False)
        except Exception as e:
            embed.add_field(name="Success", value=False, inline=False)
            embed.add_field(name="Error", value=str(e), inline=False)
            embed.color = 15548997  # red
        await ctx.message.reply(embed=embed)

    bot.command("addRename")(add_rename)

    async def add_playtime_tag(ctx: commands.Context, arg_minutes: int, arg_tag: str):
        if bot_channel and ctx.channel.id != bot_channel:
            return
        embed = make_embed(ctx)
        embed.add_field(name="Min minutes played", value=arg_minutes)
        embed.add_field(name="Tag", value=arg_tag)
        try:
            pt_config.playtime_tags[str(arg_minutes)] = arg_tag
            pt_config.save()
            embed.add_field(name="Success", value=True, inline=False)
        except Exception as e:
            embed.add_field(name="Success", value=False, inline=False)
            embed.add_field(name="Error", value=str(e), inline=False)
            embed.color = 15548997  # red
        await ctx.message.reply(embed=embed)

    bot.command("addPlaytimeTag")(add_playtime_tag)

    async def remove_tag(ctx: commands.Context, arg_playfab_id: str):
        if bot_channel and ctx.channel.id != bot_channel:
            return
        embed = make_embed(ctx)
        embed.add_field(name="PlayfabId", value=arg_playfab_id)
        try:
            current_tag = pt_config.tags.get(arg_playfab_id, None)
            if not current_tag:
                raise ValueError(
                    f"PlayfabId {arg_playfab_id} doesn't have any registered tag"
                )
            embed.add_field(name="RemovedTag", value=current_tag)
            pt_config.tags.pop(arg_playfab_id, None)
            pt_config.save()
            embed.add_field(name="Success", value=True, inline=False)
        except Exception as e:
            embed.add_field(name="Success", value=False, inline=False)
            embed.add_field(name="Error", value=str(e), inline=False)
            embed.color = 15548997  # red
        await ctx.message.reply(embed=embed)

    bot.command("removeTag")(remove_tag)

    async def remove_rename(ctx: commands.Context, arg_playfab_id: str):
        if bot_channel and ctx.channel.id != bot_channel:
            return
        embed = make_embed(ctx)
        embed.add_field(name="PlayfabId", value=arg_playfab_id)
        try:
            if not pt_config.rename:
                pt_config.rename = {}
            current_rename = pt_config.rename.get(arg_playfab_id, None)
            if not current_rename:
                raise ValueError(
                    f"PlayfabId {arg_playfab_id} doesn't have any registered rename"
                )
            embed.add_field(name="RemovedRename", value=current_rename)
            rename_cfg = pt_config.rename or {}
            rename_cfg.pop(arg_playfab_id, None)
            if not pt_config.rename:
                pt_config.rename = rename_cfg
            pt_config.save()
            embed.add_field(name="Success", value=True, inline=False)
        except Exception as e:
            embed.add_field(name="Success", value=False, inline=False)
            embed.add_field(name="Error", value=str(e), inline=False)
            embed.color = 15548997  # red
        await ctx.message.reply(embed=embed)

    bot.command("removeRename")(remove_rename)

    async def remove_playtime_tag(ctx: commands.Context, arg_minutes: str):
        if bot_channel and ctx.channel.id != bot_channel:
            return
        embed = make_embed(ctx)
        embed.add_field(name="Min minutes played", value=arg_minutes)
        try:
            current_tag = pt_config.playtime_tags.get(arg_minutes, None)
            if not current_tag:
                raise ValueError(
                    f"Min minutes played {arg_minutes} doesn't have any registered tag"
                )
            embed.add_field(name="RemovedTag", value=current_tag)
            pt_config.playtime_tags.pop(arg_minutes, None)
            pt_config.save()
            embed.add_field(name="Success", value=True, inline=False)
        except Exception as e:
            embed.add_field(name="Success", value=False, inline=False)
            embed.add_field(name="Error", value=str(e), inline=False)
            embed.color = 15548997  # red
        await ctx.message.reply(embed=embed)

    bot.command("removePlaytimeTag")(remove_playtime_tag)

    async def add_salute(ctx: commands.Context, arg_playfab_id: str, arg_salute: str):
        if bot_channel and ctx.channel.id != bot_channel:
            return
        embed = make_embed(ctx)
        embed.add_field(name="PlayfabId", value=arg_playfab_id)
        embed.add_field(name="Salute", value=arg_salute, inline=False)
        try:
            pt_config.salutes[arg_playfab_id] = arg_salute
            pt_config.save()
            embed.add_field(name="Success", value=True, inline=False)
        except Exception as e:
            embed.add_field(name="Success", value=False, inline=False)
            embed.add_field(name="Error", value=str(e), inline=False)
            embed.color = 15548997  # red
        await ctx.message.reply(embed=embed)

    bot.command("addSalute")(add_salute)

    async def remove_salute(ctx: commands.Context, arg_playfab_id: str):
        if bot_channel and ctx.channel.id != bot_channel:
            return
        embed = make_embed(ctx)
        embed.add_field(name="PlayfabId", value=arg_playfab_id)
        try:
            current_salute = pt_config.salutes.get(arg_playfab_id, None)
            if not current_salute:
                raise ValueError(
                    f"PlayfabId {arg_playfab_id} doesn't have any registered salute"
                )
            embed.add_field(name="RemovedSalute", value=current_salute, inline=False)
            pt_config.salutes.pop(arg_playfab_id, None)
            pt_config.save()
            embed.add_field(name="Success", value=True, inline=False)
        except Exception as e:
            embed.add_field(name="Success", value=False, inline=False)
            embed.add_field(name="Error", value=str(e), inline=False)
            embed.color = 15548997  # red
        await ctx.message.reply(embed=embed)

    bot.command("removeSalute")(remove_salute)

    async def get_config(ctx: commands.Context):
        if bot_channel and ctx.channel.id != bot_channel:
            return
        embed = make_embed(ctx)
        too_long: bool = False
        json_code: str = ""
        try:
            config_json = json.dumps(pt_config.__dict__, indent=2)
            json_code = f"```{config_json}```"
            config_len = len(json_code)
            too_long = config_len >= 1024 and config_len < 2000
            really_too_long = config_len >= 2000
            if really_too_long:
                json_code = "Config is too large (more than 2k characters), please consult file directly at ./persist/config.json"
            embed.add_field(
                name="Config",
                value=json_code if not too_long else "Too long, sent separately",
                inline=False,
            )
            embed.add_field(name="Success", value=True, inline=False)
        except Exception as e:
            embed.add_field(name="Success", value=False, inline=False)
            embed.add_field(name="Error", value=str(e), inline=False)
            embed.color = 15548997  # red
        await ctx.message.reply(embed=embed, content=json_code if too_long else None)

    bot.command("ptConf")(get_config)
