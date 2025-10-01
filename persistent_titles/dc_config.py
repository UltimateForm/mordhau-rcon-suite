import json
import discord
from discord.ext import commands
from common.discord import (
    BotHelper,
    make_embed as common_make_embed,
    bot_config_channel_checker,
)
from config_client.data import pt_config, bot_config
import time
import io
import os
from aiofiles import open as aio_open


def make_embed(ctx: commands.Context):
    embed = common_make_embed(str(ctx.command), color=discord.Colour(3447003))
    return embed


def register_cfg_dc_commands(bot: commands.Bot):
    bot_channel = bot_config.config_bot_channel

    @bot.group(
        invoke_without_command=False, description="Persitent titles config commands"
    )
    async def pt(ctx: commands.Context):
        if ctx.subcommand_passed is None:
            helper = bot.get_cog("BotHelper")
            if not isinstance(helper, BotHelper) or not ctx.command:
                return
            await helper.help(ctx, ctx.command.name)

    pt.add_check(bot_config_channel_checker(bot_config))

    # TODO: jesus organize commands better after things calm down
    # TODO: create custom decorator so we dont have to repeat error handling in all the below commands

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
            embed.add_field(name="Success", value=str(True), inline=False)
        except Exception as e:
            embed.add_field(name="Success", value=str(False), inline=False)
            embed.add_field(name="Error", value=str(e), inline=False)
            embed.color = 15548997  # red
        await ctx.message.reply(embed=embed)

    pt.command(
        "setTagFormat",
        description="sets the tag format, must always include {0} which is the placeholder for the tag",
        usage="<format>",
        help="-{0}-",
    )(set_tag_format)

    async def set_salute_timer(ctx: commands.Context, arg_timer: int):
        if bot_channel and ctx.channel.id != bot_channel:
            return
        embed = make_embed(ctx)
        embed.add_field(name="ArgFormat", value=f"{arg_timer} seconds")
        try:
            pt_config.salute_timer = arg_timer
            pt_config.save()
            embed.add_field(name="Success", value=str(True), inline=False)
        except Exception as e:
            embed.add_field(name="Success", value=str(False), inline=False)
            embed.add_field(name="Error", value=str(e), inline=False)
            embed.color = 15548997  # red
        await ctx.message.reply(embed=embed)

    pt.command(
        "setSaluteTimer",
        description="sets the time in seconds for salute to show up in server",
        usage="<arg_timer>",
    )(set_salute_timer)

    async def add_tag(ctx: commands.Context, arg_playfab_id: str, arg_tag: str):
        if bot_channel and ctx.channel.id != bot_channel:
            return
        embed = make_embed(ctx)
        embed.add_field(name="PlayfabId", value=arg_playfab_id)
        embed.add_field(name="Tag", value=arg_tag)
        try:
            pt_config.tags[arg_playfab_id] = arg_tag
            pt_config.save()
            embed.add_field(name="Success", value=str(True), inline=False)
        except Exception as e:
            embed.add_field(name="Success", value=str(False), inline=False)
            embed.add_field(name="Error", value=str(e), inline=False)
            embed.color = 15548997  # red
        await ctx.message.reply(embed=embed)

    pt.command(
        "addTag",
        description="adds a persistant player title, use quotes for titles that include spaces, use * in place of playfabid to add title for everyone",
        usage="<playfab_id> <title>",
        help="D98123JKAS78354 CryBaby",
    )(add_tag)

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
            embed.add_field(name="Success", value=str(True), inline=False)
        except Exception as e:
            embed.add_field(name="Success", value=str(False), inline=False)
            embed.add_field(name="Error", value=str(e), inline=False)
            embed.color = 15548997  # red
        await ctx.message.reply(embed=embed)

    pt.command(
        "addRename",
        description="sets a new username for a playfab id",
        usage="<playfab_id> <new_name>",
        help="D98123JKAS78354 ChooseABetterName",
    )(add_rename)

    async def add_playtime_tag(ctx: commands.Context, arg_minutes: int, arg_tag: str):
        if bot_channel and ctx.channel.id != bot_channel:
            return
        embed = make_embed(ctx)
        embed.add_field(name="Min minutes played", value=str(arg_minutes))
        embed.add_field(name="Tag", value=arg_tag)
        try:
            pt_config.playtime_tags[str(arg_minutes)] = arg_tag
            pt_config.save()
            embed.add_field(name="Success", value=str(True), inline=False)
        except Exception as e:
            embed.add_field(name="Success", value=str(False), inline=False)
            embed.add_field(name="Error", value=str(e), inline=False)
            embed.color = 15548997  # red
        await ctx.message.reply(embed=embed)

    pt.command(
        "addPlaytimeTag",
        description="sets playtime title for minimum time played, time must be numeric value representing minutes",
        usage="<min_time> <title>",
        help="300 Veteran",
    )(add_playtime_tag)

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
            embed.add_field(name="Success", value=str(True), inline=False)
        except Exception as e:
            embed.add_field(name="Success", value=str(False), inline=False)
            embed.add_field(name="Error", value=str(e), inline=False)
            embed.color = 15548997  # red
        await ctx.message.reply(embed=embed)

    pt.command(
        "removeTag",
        description="removes tag for playfabid",
        usage="<min_time>",
        help="300",
    )(remove_tag)

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
            embed.add_field(name="Success", value=str(True), inline=False)
        except Exception as e:
            embed.add_field(name="Success", value=str(False), inline=False)
            embed.add_field(name="Error", value=str(e), inline=False)
            embed.color = 15548997  # red
        await ctx.message.reply(embed=embed)

    pt.command(
        "removeRename",
        description="removes a rename for playfabid",
        usage="<playfab_id>",
        help="D98123JKAS78354",
    )(remove_rename)

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
            embed.add_field(name="Success", value=str(True), inline=False)
        except Exception as e:
            embed.add_field(name="Success", value=str(False), inline=False)
            embed.add_field(name="Error", value=str(e), inline=False)
            embed.color = 15548997  # red
        await ctx.message.reply(embed=embed)

    pt.command(
        "removePlaytimeTag",
        description="removes a playtime tag",
        usage="<min_time>",
        help="300",
    )(remove_playtime_tag)

    async def add_salute(ctx: commands.Context, arg_playfab_id: str, arg_salute: str):
        if bot_channel and ctx.channel.id != bot_channel:
            return
        embed = make_embed(ctx)
        embed.add_field(name="PlayfabId", value=arg_playfab_id)
        embed.add_field(name="Salute", value=arg_salute, inline=False)
        try:
            pt_config.salutes[arg_playfab_id] = arg_salute
            pt_config.save()
            embed.add_field(name="Success", value=str(True), inline=False)
        except Exception as e:
            embed.add_field(name="Success", value=str(False), inline=False)
            embed.add_field(name="Error", value=str(e), inline=False)
            embed.color = 15548997  # red
        await ctx.message.reply(embed=embed)

    pt.command(
        "addSalute",
        description="adds salute for playfab id",
        usage="<playfab_id> <salute_txt>",
        help='D98123JKAS78354 "Welcome back Dan"',
    )(add_salute)

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
            embed.add_field(name="Success", value=str(True), inline=False)
        except Exception as e:
            embed.add_field(name="Success", value=str(False), inline=False)
            embed.add_field(name="Error", value=str(e), inline=False)
            embed.color = 15548997  # red
        await ctx.message.reply(embed=embed)

    pt.command(
        "removeSalute",
        description="removes salute for playfab id",
        usage="<playfab_id>",
        help="D98123JKAS78354",
    )(remove_salute)

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
            embed.add_field(name="Success", value=str(True), inline=False)
        except Exception as e:
            embed.add_field(name="Success", value=str(False), inline=False)
            embed.add_field(name="Error", value=str(e), inline=False)
            embed.color = 15548997  # red
        await ctx.message.reply(embed=embed, content=json_code if too_long else None)

    pt.command("ptConf", description="show the persistent titles config")(get_config)

    async def export_night(ctx: commands.Context):
        embed = make_embed(ctx)
        try:
            playtime_tags = pt_config.playtime_tags
            custom_ranks = pt_config.tags or {}

            tag_items = [(int(minutes), tag) for minutes, tag in playtime_tags.items()]
            tag_items.sort(key=lambda x: x[0], reverse=True)

            ranks: list[dict] = []
            player_ranks: list[dict] = []

            base_weight = 100
            for idx, (minutes, tag) in enumerate(tag_items):
                hours = round(minutes / 60, 2)
                ranks.append(
                    {
                        "Name": tag,
                        "Weight": base_weight + idx * 100,
                        "Prefix": pt_config.tag_format.format(tag) + " ",
                        "GiveOnPlaytime": hours,
                    }
                )

            export_obj = {"Ranks": ranks, "PlayerRanks": player_ranks}
            for playfab_id, tag in custom_ranks.items():
                if playfab_id == "*":
                    continue

                if not any(rank["Name"] == tag for rank in ranks):
                    ranks.append(
                        {
                            "Name": tag,
                            "Weight": 50,
                            "Prefix": pt_config.tag_format.format(tag) + " ",
                        }
                    )
                player_ranks.append(
                    {
                        "PlayfabID": playfab_id,
                        "Rank": tag,
                    }
                )
            json_str = json.dumps(export_obj, indent=2)
            ti = int(time.time())
            file_name = f"night_export_{ti}.json"
            persist_dir = "./persist"
            file_path = os.path.join(persist_dir, file_name)
            async with aio_open(file_path, "w") as f:
                await f.write(json_str)
            file = discord.File(
                fp=io.BytesIO(json_str.encode("utf-8")),
                filename=file_name,
                description="Exported Night's mod ranks data",
            )
            await ctx.message.reply(
                f"Exported Night's mod ranks. Also written to `{file_path}`",
                file=file,
            )
        except Exception as e:
            embed.add_field(name="Success", value=str(False), inline=False)
            embed.add_field(name="Error", value=str(type(e)), inline=False)
            embed.add_field(
                name="Hint",
                value="File might have still exported, check `./persist` folder",
                inline=False,
            )
            embed.color = 15548997  # red
            await ctx.message.reply(embed=embed)

    pt.command(
        "exportNight",
        description="exports persistent titles config in format compatible with Night's mods i.e. https://mod.io/g/mordhau/m/playtime-tracker",
    )(export_night)
