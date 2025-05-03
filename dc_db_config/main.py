import discord
from discord.ext import commands
from motor.motor_asyncio import AsyncIOMotorCollection
from config_client.models import BotConfig
from common.discord import (
    BotHelper,
    bot_config_channel_checker,
    make_embed as common_make_embed,
)
from pymongo import UpdateOne


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

    @commands.group(invoke_without_command=False, description="DB admin commands")
    async def db(self, ctx: commands.Context):
        if ctx.subcommand_passed is None:
            helper = self._client.get_cog("BotHelper")
            if not isinstance(helper, BotHelper) or not ctx.command:
                return
            await helper.help(ctx, ctx.command.name)

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
