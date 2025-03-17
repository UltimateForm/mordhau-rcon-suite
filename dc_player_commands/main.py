import asyncio
import discord
from discord.ext.commands import Bot, Context
from common import logger, parsers
from common.compute import make_ordinal
from common.discord import make_embed as common_make_embed
from motor.motor_asyncio import (
    AsyncIOMotorDatabase,
)
from rank_compute.playtime import get_playtime
from rcon.rcon import RconContext
from rank_compute.kills import get_kills, get_season_kills
from config_client.models import SeasonConfig
import re


def register_dc_player_commands(bot: Bot, db: AsyncIOMotorDatabase):
    def make_embed(ctx: Context):
        embed = common_make_embed(str(ctx.command), color=discord.Colour(3447003))
        return embed

    def rank_2_emoji(n: int):
        rank_emoji_map = {0: ":first_place:", 1: ":second_place:", 2: ":third_place:"}
        rank_out = rank_emoji_map.get(n, make_ordinal(n + 1))
        return rank_out

    async def kdr(ctx: Context, argument: str):
        collection = db["kills"]

        try:
            embed = make_embed(ctx)
            embed.color = 0xFFFC2E
            kill_score = await get_kills(argument, collection)
            if kill_score is None:
                raise Exception("Not found")
            embed.add_field(
                name="Rank",
                value=rank_2_emoji(kill_score.rank) if kill_score.rank else "None",
                inline=False,
            )
            embed.add_field(name="PlayfabId", value=kill_score.player_id)
            embed.add_field(name="Username", value=kill_score.user_name)
            embed.add_field(name=chr(173), value=chr(173))
            embed.add_field(name="Kills", value=kill_score.kill_count)
            embed.add_field(name="Deaths", value=kill_score.death_count)
            embed.add_field(name="Ratio", value=kill_score.ratio or "-")
            if len(kill_score.achievements):
                embed.add_field(name="", value="\n")
                embed.add_field(
                    name=":trophy: Achievements :trophy:", value="\n", inline=False
                )
                awards = []
                for k, v in kill_score.achievements.items():
                    rank = rank_2_emoji(v - 1)
                    if k == "lifetime_rank":
                        awards.append(f"**Lifetime** {rank}")
                    else:
                        awards.append(f"**{k}** {rank}")
                embed.add_field(name="", value="〡".join(awards))
        except Exception as e:
            logger.error(str(e))
            embed = make_embed(ctx)
            embed.add_field(name="Success", value=False, inline=False)
            embed.add_field(name="Error", value=str(e), inline=False)
            embed.color = 15548997  # red
        await ctx.message.reply(embed=embed)

    bot.command(
        "kdr", description="gets kdr score for player", usage="<playfab_id_or_username>"
    )(kdr)

    async def skdr(ctx: Context, argument: str):
        collection = db["kills"]
        embed = make_embed(ctx)
        embed.color = 0xFFFC2E
        try:
            exists = await SeasonConfig.aexists()
            if not exists:
                raise Exception("No active season")
            season_cfg = await SeasonConfig.aload()
            if not season_cfg.is_active:
                raise Exception("No active season")
            kill_score = await get_season_kills(argument, collection, season_cfg)
            if kill_score is None:
                raise Exception("Not found")
            embed.add_field(
                name="Rank",
                value=rank_2_emoji(kill_score.rank) if kill_score.rank else "None",
                inline=False,
            )
            embed.title = season_cfg.embed_config.title
            embed.description = season_cfg.embed_config.description
            embed.set_footer(text=embed.footer.text, icon_url=embed.footer.icon_url)
            embed.color = 15844367
            embed.add_field(name="PlayfabId", value=kill_score.player_id)
            embed.add_field(name="Username", value=kill_score.user_name)
            embed.add_field(name=chr(173), value=chr(173))
            embed.add_field(name="Kills", value=kill_score.kill_count)
            embed.add_field(name="Deaths", value=kill_score.death_count)
            embed.add_field(name="Ratio", value=kill_score.ratio or "-")
        except Exception as e:
            embed.add_field(name="Success", value=False, inline=False)
            embed.add_field(name="Error", value=str(e), inline=False)
            embed.color = 15548997  # red
        await ctx.message.reply(embed=embed)

    bot.command(
        "skdr",
        description="gets current seasion kdr score for player",
        usage="<playfab_id_or_username>",
    )(skdr)

    async def playtime(ctx: Context, argument: str):
        collection = db["playtime"]
        embed = make_embed(ctx)
        embed.color = 0x43FF2E
        try:
            player_score = await get_playtime(argument, collection)
            if player_score is None:
                raise Exception("Not found")
            embed.add_field(
                name="Rank", value=rank_2_emoji(player_score.rank), inline=False
            )
            embed.add_field(name="PlayfabId", value=player_score.player_id)
            embed.add_field(name="Username", value=player_score.user_name)
            embed.add_field(
                name="Time played", value=player_score.time_txt, inline=False
            )
        except Exception as e:
            embed.add_field(name="Success", value=False, inline=False)
            embed.add_field(name="Error", value=str(e), inline=False)
            embed.color = 15548997  # red
        await ctx.message.reply(embed=embed)

    bot.command(
        "playtime",
        description="gets playtime score for player",
        usage="<playfab_id_or_username>",
    )(playtime)

    async def playerlist(ctx: Context):
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

    bot.command("playerlist", description="shows online players list")(playerlist)

    async def versus(ctx: Context, player1: str, player2: str):
        embed = make_embed(ctx)
        embed.description = "(shows how many times players have killed each other)"
        collection = db["kills"]
        embed.color = 0x080808
        try:
            data: list[dict] = []
            for player in [player1, player2]:
                query: dict = {}
                if parsers.is_playfab_id_format(player):
                    query = {"playfab_id": player}
                else:
                    query = {"user_name": re.compile(f".*{player}.*", re.IGNORECASE)}
                r = await collection.find_one(query)
                if r is None:
                    raise Exception(f"{player} not found")
                data.append(r)
            player1_data = data[0]
            player2_data = data[1]
            player1_id = player1_data.get("playfab_id", None)
            player2_id = player2_data.get("playfab_id", None)
            player1_kills: dict = player1_data.get("kills", {})
            player2_kills: dict = player2_data.get("kills", {})
            embed.add_field(
                name=player1_data.get("user_name"),
                value=player1_kills.get(player2_id, 0),
            )
            embed.add_field(name=":vs:", value="")
            embed.add_field(
                name=player2_data.get("user_name"),
                value=player2_kills.get(player1_id, 0),
            )
        except Exception as e:
            embed.add_field(name="Success", value=False, inline=False)
            embed.add_field(name="Error", value=str(e), inline=False)
            embed.color = 15548997  # red
        await ctx.message.reply(embed=embed)

    bot.command(
        "versus",
        description="shows battle tally between two players, as in how many times they've killed each other",
        usage="<playfab_id_or_username> <playfab_id_or_username>",
        aliases=["vs"],
    )(versus)
