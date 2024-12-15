import asyncio
import aiofiles
import discord
from discord.ext import tasks
from datetime import datetime, timezone
from motor.motor_asyncio import (
    AsyncIOMotorCollection,
)
from table2ascii import table2ascii as t2a
from common import logger

from common.compute import compute_time_txt

BOARD_REFRESH_TIME = bot_config.playtime_refresh_time or 60


# TODO: create base class for these boards, too much duplication
class PlayTimeScoreboard(discord.Client):
    _channel_id: int = 0
    _channel: discord.TextChannel | None = None
    _current_message: discord.Message | None = None
    _playtime_collection: AsyncIOMotorCollection | None
    file_path = "./persist/playtime_msg_id"

    def __init__(
        self,
        channel_id: int,
        playtime_collection: AsyncIOMotorCollection | NameError,
        intents: discord.Intents,
        **kwargs,
    ):
        self._channel_id = channel_id
        self._playtime_collection = playtime_collection
        super().__init__(intents=intents, **kwargs)

    async def on_ready(self):
        logger.info(f"Retrieving playtime scoreboard channel {self._channel_id}")
        self._channel = await self.fetch_channel(self._channel_id)
        await self.delete_previous_message()
        self.job.start()

    async def write_msg_id(self):
        async with aiofiles.open(self.file_path, "w") as file:
            await file.write(str(self._current_message.id))

    async def delete_previous_message(self) -> str | None:
        try:
            file_exists = await aiofiles.os.path.exists(self.file_path)
            if not file_exists:
                return
            msg_id: str | None = ""
            async with aiofiles.open(self.file_path, "r") as file:
                msg_id = await file.read()
            if not msg_id.isdecimal():
                return
            parsed_msg_id = int(msg_id)
            msg = await self._channel.fetch_message(parsed_msg_id)
            await msg.delete()
        except Exception as e:
            logger.error(f"PlayTimeScoreboard: Error deleting existing board: {e}")

    async def send_board(self):
        top_20_items: list[dict] = (
            await self._playtime_collection.find()
            .sort("minutes", -1)
            .limit(20)
            .to_list()
        )
        ascii_table = (
            "```"
            + t2a(
                header=["Rank", "Username", "Time"],
                body=[
                    [
                        index + 1,
                        item.get("user_name", None)
                        or item.get("playfab_id", "<UNKNOWN>"),
                        compute_time_txt(item["minutes"]),
                    ]
                    for (index, item) in enumerate(top_20_items)
                ],
            )
            + "```"
        )
        current_time = round(datetime.now(timezone.utc).timestamp())
        time_sig = f"Last updated: <t:{current_time}> (<t:{current_time}:R>)"
        embed = discord.Embed(
            title="<:ClockofDestiny:1310130670798110810> PLAYTIME LEADERBOARD (TOP 20) <:ClockofDestiny:1310130670798110810>",
            description=time_sig + "\n" + ascii_table,
            color=discord.Colour(int("1eff00", 16)),
        )
        embed.set_footer(
            text=f"""
Updates every {compute_time_txt(BOARD_REFRESH_TIME/60)}
Data has been collecting since 5/25/2024
                """
        )
        if not self._current_message:
            self._current_message = await self._channel.send(embed=embed)
            asyncio.create_task(self.write_msg_id())
        else:
            await self._current_message.edit(embed=embed)

    @tasks.loop(seconds=BOARD_REFRESH_TIME)
    async def job(self):
        await self.send_board()


if __name__ == "__main__":
    from motor.motor_asyncio import (
        AsyncIOMotorClient,
        AsyncIOMotorCollection,
    )

    def load_db() -> tuple[AsyncIOMotorCollection, AsyncIOMotorCollection] | None:
        db_connection = bot_config.db_connection_string
        db_name = bot_config.db_name
        if db_name is None or db_connection is None:
            print(
                "DB config incomplete, either missing DB_CONNECTION_STRING or DB_NAME from environment variables"
            )
            return None
        db_client = AsyncIOMotorClient(db_connection)
        database = db_client[db_name]
        playtime_collection = database["playtime"]
        live_sessions_collection = database["live_session"]
        return (live_sessions_collection, playtime_collection)

    intents = discord.Intents.default()
    intents.message_content = True
    (_, playtime_collection) = load_db()
    playtime_channel = bot_config.playtime_channel

    playtime_scoreboard = PlayTimeScoreboard(
        playtime_channel, playtime_collection, intents=intents
    )
    playtime_scoreboard.run(token=bot_config.d_token)
