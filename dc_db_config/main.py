import io
import json
import time
import discord
from discord.ext import commands
from motor.motor_asyncio import AsyncIOMotorCollection
from common import logger
import os
from config_client.models import BotConfig
from common.discord import (
    BotHelper,
    bot_config_channel_checker,
    make_embed as common_make_embed,
)
from pymongo import UpdateOne
from aiofiles import open as aio_open


class DcDbConfig(commands.Cog):
    _client: commands.Bot
    _cfg: BotConfig
    _playtime_collection: AsyncIOMotorCollection
    _kills_collection: AsyncIOMotorCollection
    _cmd_group: commands.Group

    def __init__(
        self,
        client: commands.Bot,
        bot_config: BotConfig,
        playtime_collection: AsyncIOMotorCollection,
        kills_collection: AsyncIOMotorCollection,
    ) -> None:
        self._client = client
        self._cfg = bot_config
        self._playtime_collection = playtime_collection
        self._kills_collection = kills_collection
        self.db.add_check(bot_config_channel_checker(bot_config))
        super().__init__()

    def make_embed(self, ctx: commands.Context):
        embed = common_make_embed(str(ctx.command), color=discord.Colour(2899536))
        return embed

    async def _aggregate_playtime_record(self) -> dict:
        pipeline = [
            {
                "$project": {
                    "_id": 0,
                    "k": "$playfab_id",
                    "v": {"$divide": ["$minutes", 60]},
                }
            },
            {"$group": {"_id": None, "data": {"$push": "$$ROOT"}}},
            {"$project": {"_id": 0, "map": {"$arrayToObject": "$data"}}},
        ]
        result = self._playtime_collection.aggregate(pipeline)
        first_doc = await result.to_list(length=1)
        if not first_doc or "map" not in first_doc[0]:
            raise Exception("Failed to get playtime map from aggregation")
        return first_doc[0]["map"]

    async def _aggregate_kills_record(self) -> dict:
        pipeline = [
            {
                "$project": {
                    "_id": 0,
                    "k": "$playfab_id",
                    "v": {"k": "$kill_count", "d": "$death_count"},
                }
            },
            {"$group": {"_id": None, "data": {"$push": "$$ROOT"}}},
            {"$project": {"_id": 0, "map": {"$arrayToObject": "$data"}}},
        ]
        result = self._kills_collection.aggregate(pipeline)
        first_doc = await result.to_list(length=1)
        if not first_doc or "map" not in first_doc[0]:
            raise Exception("Failed to get kills map from aggregation")
        return first_doc[0]["map"]

    async def _respond_with_written_file(
        self,
        ctx: commands.Context,
        record: object,
        filename_prefix: str,
        description: str,
    ) -> None:
        json_str = json.dumps(record, indent=2)
        ti = int(time.time())
        file_name = f"{filename_prefix}_{ti}.json"
        persist_path = f"./persist/{file_name}"
        # ensure persist dir exists
        os.makedirs("./persist", exist_ok=True)
        async with aio_open(persist_path, "w") as f:
            await f.write(json_str)
        file = discord.File(
            fp=io.BytesIO(json_str.encode("utf-8")),
            filename=file_name,
            description=description,
        )
        await ctx.message.reply(
            f"{description}. Also written to `{persist_path}`", file=file
        )

    @commands.group(invoke_without_command=False, description="DB admin commands")
    async def db(self, ctx: commands.Context):
        if ctx.subcommand_passed is None:
            helper = self._client.get_cog("BotHelper")
            if not isinstance(helper, BotHelper) or not ctx.command:
                return
            await helper.help(ctx, ctx.command.name)  # type: ignore

    @db.command(
        description="change a player's name in DB",
        usage="<plafayb_id> <new_name>",
    )
    async def chg_name(self, ctx: commands.Context, playfab_id: str, new_name: str):
        if (
            self._cfg.config_bot_channel
            and ctx.channel.id != self._cfg.config_bot_channel
        ):
            return
        embed = self.make_embed(ctx)
        try:
            update = UpdateOne(
                {"playfab_id": playfab_id}, {"$set": {"user_name": new_name}}
            )
            update_kills = await self._kills_collection.bulk_write([update])
            update_playtime = await self._playtime_collection.bulk_write([update])
            if update_kills.matched_count < 1 or update_playtime.matched_count < 1:
                raise Exception(
                    f"One or more collections failed to update.\n- Playtime matched players: {update_playtime.matched_count}\n- Kills matched players: {update_kills.matched_count}"
                )
            embed.add_field(name="Success", value=str(True))
            await ctx.reply(embed=embed)
        except Exception as e:
            embed.add_field(name="Success", value=str(False), inline=False)
            embed.add_field(name="Error", value=str(e), inline=False)
            embed.color = 15548997  # red
            await ctx.message.reply(embed=embed)

    @db.command(
        description="show metadata of db",
    )
    async def metadata(self, ctx: commands.Context):
        if (
            self._cfg.config_bot_channel
            and ctx.channel.id != self._cfg.config_bot_channel
        ):
            return
        embed = self.make_embed(ctx)
        try:
            kills_player_count = await self._kills_collection.estimated_document_count()
            playtime_player_count = (
                await self._playtime_collection.estimated_document_count()
            )

            embed.add_field(
                name="Playtime Registered Players",
                value=f"{playtime_player_count} (estimated)",
            )
            embed.add_field(
                name="Kills Registered Players",
                value=f"{kills_player_count} (estimated)",
            )

            await ctx.reply(embed=embed)
        except Exception as e:
            embed.add_field(name="Success", value=str(False), inline=False)
            embed.add_field(name="Error", value=str(e), inline=False)
            embed.color = 15548997  # red
            await ctx.message.reply(embed=embed)

    @db.command(
        description="export playtime data as json, compatible with server side mods such as Night's Playtime. Will also write the export to ./persist/ folder"
    )
    async def export_playtime(self, ctx: commands.Context):
        if (
            self._cfg.config_bot_channel
            and ctx.channel.id != self._cfg.config_bot_channel
        ):
            return
        embed = self.make_embed(ctx)
        try:
            playtime_record = await self._aggregate_playtime_record()
            await self._respond_with_written_file(
                ctx, playtime_record, "playtime_export", "Exported playtime data"
            )
        except Exception as e:
            logger.error(f"Failed to export playtime: {e}")
            embed.add_field(name="Success", value=str(False), inline=False)
            embed.add_field(name="Error", value=str(type(e)), inline=False)
            embed.add_field(
                name="Hint",
                value="Check logs for details, and check folder `./persist/`, file might have been created there",
                inline=False,
            )
            embed.color = 15548997  # red
            await ctx.message.reply(embed=embed)

    @db.command(
        description="export kills/deaths data as json. Will also write the export to ./persist/ folder"
    )
    async def export_kills(self, ctx: commands.Context):
        if (
            self._cfg.config_bot_channel
            and ctx.channel.id != self._cfg.config_bot_channel
        ):
            return
        embed = self.make_embed(ctx)
        try:
            kills_recor = await self._aggregate_kills_record()
            await self._respond_with_written_file(
                ctx, kills_recor, "kills_export", "Exported kills data"
            )
        except Exception as e:
            logger.error(f"Failed to export kills: {e}")
            embed.add_field(name="Success", value=str(False), inline=False)
            embed.add_field(name="Error", value=str(type(e)), inline=False)
            embed.add_field(
                name="Hint",
                value="Check logs for details, and check folder `./persist/`, file might have been created there",
                inline=False,
            )
            embed.color = 15548997  # red
            await ctx.message.reply(embed=embed)

    @db.command(
        description="export both kills and playtime into a single json file. Will also write the export to ./persist/ folder"
    )
    async def export_all(self, ctx: commands.Context):
        if (
            self._cfg.config_bot_channel
            and ctx.channel.id != self._cfg.config_bot_channel
        ):
            return
        embed = self.make_embed(ctx)
        try:
            playmap = await self._aggregate_playtime_record()
            killsmap = await self._aggregate_kills_record()
            combined = {"kills": killsmap, "playtime": playmap}
            await self._respond_with_written_file(
                ctx,
                combined,
                "kills_playtime_export",
                "Exported kills and playtime data",
            )
        except Exception as e:
            logger.error(f"Failed to export both: {e}")
            embed.add_field(name="Success", value=str(False), inline=False)
            embed.add_field(name="Error", value=str(type(e)), inline=False)
            embed.add_field(
                name="Hint",
                value="Check logs for details, and check folder `./persist/`, file might have been created there",
                inline=False,
            )
            embed.color = 15548997  # red
            await ctx.message.reply(embed=embed)
