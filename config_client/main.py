import asyncio
import os
import json
import discord
from discord.ext import commands
from common import parsers
from common.compute import compute_time_txt
from config_client.data import Config, load_config, save_config
from motor.motor_asyncio import (
    AsyncIOMotorDatabase,
)

from rcon.rcon import RconContext

intents = discord.Intents.default()
intents.message_content = True

config_bot = commands.Bot(command_prefix=".", intents=intents)

config: Config = load_config()


def make_embed(ctx: commands.Context, footer=""):
    embed = discord.embeds.Embed(title=ctx.command, color=3447003)  # blue
    embed.set_footer(
        text="Bot source: https://github.com/UltimateForm/mordhau-rcon-suite"
    )
    return embed


@config_bot.command()
async def ping(ctx: commands.Context):
    await ctx.message.reply(":ping_pong:")

# TODO: jesus organize commands better after things calm down
# TODO: create custom decorator so we dont have to repeat error handling in all the below commands

bot_channel = int(os.environ.get("CONFIG_BOT_CHANNEL", "0"))


@config_bot.command("setTagFormat")
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
        config.tag_format = arg_format
        save_config(config)
        embed.add_field(name="Success", value=True, inline=False)
    except Exception as e:
        embed.add_field(name="Success", value=False, inline=False)
        embed.add_field(name="Error", value=str(e), inline=False)
        embed.color = 15548997  # red
    await ctx.message.reply(embed=embed)


@config_bot.command("setSaluteTimer")
async def set_salute_timer(ctx: commands.Context, arg_timer: int):
    if bot_channel and ctx.channel.id != bot_channel:
        return
    embed = make_embed(ctx)
    embed.add_field(name="ArgFormat", value=f"{arg_timer} seconds")
    try:
        config.salute_timer = arg_timer
        save_config(config)
        embed.add_field(name="Success", value=True, inline=False)
    except Exception as e:
        embed.add_field(name="Success", value=False, inline=False)
        embed.add_field(name="Error", value=str(e), inline=False)
        embed.color = 15548997  # red
    await ctx.message.reply(embed=embed)


@config_bot.command("addTag")
async def add_tag(ctx: commands.Context, arg_playfab_id: str, arg_tag: str):
    if bot_channel and ctx.channel.id != bot_channel:
        return
    embed = make_embed(ctx)
    embed.add_field(name="PlayfabId", value=arg_playfab_id)
    embed.add_field(name="Tag", value=arg_tag)
    try:
        config.tags[arg_playfab_id] = arg_tag
        save_config(config)
        embed.add_field(name="Success", value=True, inline=False)
    except Exception as e:
        embed.add_field(name="Success", value=False, inline=False)
        embed.add_field(name="Error", value=str(e), inline=False)
        embed.color = 15548997  # red
    await ctx.message.reply(embed=embed)


@config_bot.command("addRename")
async def add_rename(ctx: commands.Context, arg_playfab_id: str, arg_rename: str):
    if bot_channel and ctx.channel.id != bot_channel:
        return
    embed = make_embed(ctx)
    embed.add_field(name="PlayfabId", value=arg_playfab_id)
    embed.add_field(name="Rename", value=arg_rename)
    try:
        config.rename[arg_playfab_id] = arg_rename
        save_config(config)
        embed.add_field(name="Success", value=True, inline=False)
    except Exception as e:
        embed.add_field(name="Success", value=False, inline=False)
        embed.add_field(name="Error", value=str(e), inline=False)
        embed.color = 15548997  # red
    await ctx.message.reply(embed=embed)


@config_bot.command("addPlaytimeTag")
async def add_playtime_tag(ctx: commands.Context, arg_minutes: int, arg_tag: str):
    if bot_channel and ctx.channel.id != bot_channel:
        return
    embed = make_embed(ctx)
    embed.add_field(name="Min minutes played", value=arg_minutes)
    embed.add_field(name="Tag", value=arg_tag)
    try:
        config.playtime_tags[str(arg_minutes)] = arg_tag
        save_config(config)
        embed.add_field(name="Success", value=True, inline=False)
    except Exception as e:
        embed.add_field(name="Success", value=False, inline=False)
        embed.add_field(name="Error", value=str(e), inline=False)
        embed.color = 15548997  # red
    await ctx.message.reply(embed=embed)


@config_bot.command("removeTag")
async def remove_tag(ctx: commands.Context, arg_playfab_id: str):
    if bot_channel and ctx.channel.id != bot_channel:
        return
    embed = make_embed(ctx)
    embed.add_field(name="PlayfabId", value=arg_playfab_id)
    try:
        current_tag = config.tags.get(arg_playfab_id, None)
        if not current_tag:
            raise ValueError(
                f"PlayfabId {arg_playfab_id} doesn't have any registered tag"
            )
        embed.add_field(name="RemovedTag", value=current_tag)
        config.tags.pop(arg_playfab_id, None)
        save_config(config)
        embed.add_field(name="Success", value=True, inline=False)
    except Exception as e:
        embed.add_field(name="Success", value=False, inline=False)
        embed.add_field(name="Error", value=str(e), inline=False)
        embed.color = 15548997  # red
    await ctx.message.reply(embed=embed)


@config_bot.command("removeRename")
async def remove_rename(ctx: commands.Context, arg_playfab_id: str):
    if bot_channel and ctx.channel.id != bot_channel:
        return
    embed = make_embed(ctx)
    embed.add_field(name="PlayfabId", value=arg_playfab_id)
    try:
        current_rename = config.rename.get(arg_playfab_id, None)
        if not current_rename:
            raise ValueError(
                f"PlayfabId {arg_playfab_id} doesn't have any registered rename"
            )
        embed.add_field(name="RemovedRename", value=current_rename)
        config.rename.pop(arg_playfab_id, None)
        save_config(config)
        embed.add_field(name="Success", value=True, inline=False)
    except Exception as e:
        embed.add_field(name="Success", value=False, inline=False)
        embed.add_field(name="Error", value=str(e), inline=False)
        embed.color = 15548997  # red
    await ctx.message.reply(embed=embed)


@config_bot.command("removePlaytimeTag")
async def remove_playtime_tag(ctx: commands.Context, arg_minutes: str):
    if bot_channel and ctx.channel.id != bot_channel:
        return
    embed = make_embed(ctx)
    embed.add_field(name="Min minutes played", value=arg_minutes)
    try:
        current_tag = config.playtime_tags.get(arg_minutes, None)
        if not current_tag:
            raise ValueError(
                f"Min minutes played {arg_minutes} doesn't have any registered tag"
            )
        embed.add_field(name="RemovedTag", value=current_tag)
        config.playtime_tags.pop(arg_minutes, None)
        save_config(config)
        embed.add_field(name="Success", value=True, inline=False)
    except Exception as e:
        embed.add_field(name="Success", value=False, inline=False)
        embed.add_field(name="Error", value=str(e), inline=False)
        embed.color = 15548997  # red
    await ctx.message.reply(embed=embed)


@config_bot.command("addSalute")
async def add_salute(ctx: commands.Context, arg_playfab_id: str, arg_salute: str):
    if bot_channel and ctx.channel.id != bot_channel:
        return
    embed = make_embed(ctx)
    embed.add_field(name="PlayfabId", value=arg_playfab_id)
    embed.add_field(name="Salute", value=arg_salute, inline=False)
    try:
        config.salutes[arg_playfab_id] = arg_salute
        save_config(config)
        embed.add_field(name="Success", value=True, inline=False)
    except Exception as e:
        embed.add_field(name="Success", value=False, inline=False)
        embed.add_field(name="Error", value=str(e), inline=False)
        embed.color = 15548997  # red
    await ctx.message.reply(embed=embed)


@config_bot.command("removeSalute")
async def remove_salute(ctx: commands.Context, arg_playfab_id: str):
    if bot_channel and ctx.channel.id != bot_channel:
        return
    embed = make_embed(ctx)
    embed.add_field(name="PlayfabId", value=arg_playfab_id)
    try:
        current_salute = config.salutes.get(arg_playfab_id, None)
        if not current_salute:
            raise ValueError(
                f"PlayfabId {arg_playfab_id} doesn't have any registered salute"
            )
        embed.add_field(name="RemovedSalute", value=current_salute, inline=False)
        config.salutes.pop(arg_playfab_id, None)
        save_config(config)
        embed.add_field(name="Success", value=True, inline=False)
    except Exception as e:
        embed.add_field(name="Success", value=False, inline=False)
        embed.add_field(name="Error", value=str(e), inline=False)
        embed.color = 15548997  # red
    await ctx.message.reply(embed=embed)


@config_bot.command("ptConf")
async def get_config(ctx: commands.Context):
    if bot_channel and ctx.channel.id != bot_channel:
        return
    embed = make_embed(ctx)
    too_long: bool = False
    json_code: str = ""
    try:
        config_json = json.dumps(config.__dict__, indent=2)
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


# PLAYER COMMANDS


DATABASE: AsyncIOMotorDatabase | None = None


def rank_2_emoji(n: int):
    rank_emoji_map = {0: ":first_place:", 1: ":second_place:", 2: ":third_place:"}
    rank_out = rank_emoji_map.get(n, str(n + 1))
    return rank_out


@config_bot.command("kdr")
async def kdr(ctx: commands.Context, argument: str):
    collection = DATABASE["kills"]
    query: dict = {}
    if parsers.is_playfab_id_format(argument):
        query = {"playfab_id": argument}
    else:
        query = {"user_name": {"$regex": argument}}
    kill_rec: dict = await collection.find_one(query)
    embed = make_embed(ctx)
    try:
        if kill_rec is None:
            raise Exception("Not found")

        user_name = kill_rec.get("user_name", "<Unknown>")
        kill_count = kill_rec.get("kill_count", 0)
        rank = await collection.count_documents({"kill_count": {"$gt": kill_count}})
        death_count = kill_rec.get("death_count", 0)
        ratio = str(round(kill_count / death_count, 2)) if death_count > 0 else "-"
        embed.add_field(name="Rank", value=rank_2_emoji(rank), inline=False)
        embed.add_field(name="PlayfabId", value=kill_rec["playfab_id"])
        embed.add_field(name="Username", value=user_name)
        embed.add_field(name=chr(173), value=chr(173))
        embed.add_field(name="Kills", value=kill_count)
        embed.add_field(name="Deaths", value=death_count)
        embed.add_field(name="Ratio", value=ratio)
    except Exception as e:
        embed.add_field(name="Success", value=False, inline=False)
        embed.add_field(name="Error", value=str(e), inline=False)
        embed.color = 15548997  # red
    await ctx.message.reply(embed=embed)


@config_bot.command("playtime")
async def playtime(ctx: commands.Context, argument: str):
    collection = DATABASE["playtime"]
    query: dict = {}
    if parsers.is_playfab_id_format(argument):
        query = {"playfab_id": argument}
    else:
        query = {"user_name": {"$regex": argument}}
    playtime_rec: dict = await collection.find_one(query)
    embed = make_embed(ctx)
    try:
        if playtime_rec is None:
            raise Exception("Not found")
        user_name = playtime_rec.get("user_name", "<Unknown>")
        minutes = playtime_rec.get("minutes", 0)
        rank = await collection.count_documents({"minutes": {"$gt": minutes}})
        time_txt = compute_time_txt(minutes)
        embed.add_field(name="Rank", value=rank_2_emoji(rank), inline=False)
        embed.add_field(name="PlayfabId", value=playtime_rec["playfab_id"])
        embed.add_field(name="Username", value=user_name)
        embed.add_field(name="Time played", value=time_txt, inline=False)
    except Exception as e:
        embed.add_field(name="Success", value=False, inline=False)
        embed.add_field(name="Error", value=str(e), inline=False)
        embed.color = 15548997  # red
    await ctx.message.reply(embed=embed)


@config_bot.command("playerlist")
async def playerlist(ctx: commands.Context):
    embed = make_embed(ctx)
    try:
        player_list_raw: str = ""
        async with asyncio.timeout(30):
            async with RconContext() as client:
                player_list_raw = await client.execute("playerlist")
        players = parsers.parse_playerlist(player_list_raw)

        players_text = (
            "\n".join(
                [f"{player.player_id} - {player.user_name}" for player in players]
            )
            if len(players)
            else "No players online"
        )
        await ctx.reply("```" + players_text + "```")
        return
    except Exception as e:
        embed.add_field(name="Success", value=False, inline=False)
        embed.add_field(name="Error", value=str(e), inline=False)
        embed.color = 15548997  # red
    await ctx.message.reply(embed=embed)


@config_bot.command("versus")
async def versus(ctx: commands.Context, player1: str, player2: str):
    embed = make_embed(ctx)
    embed.description = "(shows how many times players have killed each other)"
    collection = DATABASE["kills"]
    try:
        queries: list[dict] = []
        for player in [player1, player2]:
            if parsers.is_playfab_id_format(player):
                queries.append({"playfab_id": player})
            else:
                queries.append({"user_name": {"$regex": player}})
        data: list[dict] = []
        for query in queries:
            r = await collection.find_one(query)
            if r is None:
                query_target = query.get(
                    "playfab_id", query.get("user_name", {}).get("$regex", None)
                )
                raise Exception(f"{query_target} not found")
            data.append(r)
        player1_data = data[0]
        player2_data = data[1]
        player1_id = player1_data.get("playfab_id", None)
        player2_id = player2_data.get("playfab_id", None)
        player1_kills: dict = player1_data.get("kills", {})
        player2_kills: dict = player2_data.get("kills", {})
        embed.add_field(
            name=player1_data.get("user_name"), value=player1_kills.get(player2_id, 0)
        )
        embed.add_field(name=":vs:", value="")
        embed.add_field(
            name=player2_data.get("user_name"), value=player2_kills.get(player1_id, 0)
        )
    except Exception as e:
        embed.add_field(name="Success", value=False, inline=False)
        embed.add_field(name="Error", value=str(e), inline=False)
        embed.color = 15548997  # red
    await ctx.message.reply(embed=embed)
