import os
import discord
from discord.ext import tasks
from datetime import datetime, timezone
from motor.motor_asyncio import (
    AsyncIOMotorCollection,
)
from table2ascii import table2ascii as t2a
from common import logger

from common.compute import compute_time_txt

BOARD_REFRESH_TIME = int(os.environ.get("PLAYTIME_REFRESH_TIME", 60))


class PlayTimeScoreboard(discord.Client):
    _channel_id: int = 0
    _channel: discord.TextChannel | None = None
    _current_message: discord.Message | None = None
    _playtime_collection: AsyncIOMotorCollection | None

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
        self.job.start()

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
            title=":clock4: PLAYTIME RECORDS (top 20) :clock4:",
            description=time_sig + "\n" + ascii_table,
            color=discord.Colour(15844367),
        )
        embed.set_footer(
            text=f"""
Updates every {compute_time_txt(BOARD_REFRESH_TIME/60)}
Unknown players will be shown by playfab id only, login and logout to capture username
Bot source: https://github.com/UltimateForm/mordhau-rcon-suite
                """
        )
        if not self._current_message:
            self._current_message = await self._channel.send(embed=embed)
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
        db_connection = os.environ.get("DB_CONNECTION_STRING", None)
        db_name = os.environ.get("DB_NAME", None)
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
    playtime_channel = int(os.environ.get("PLAYTIME_CHANNEL", 0))

    playtime_scoreboard = PlayTimeScoreboard(
        playtime_channel, playtime_collection, intents=intents
    )
    playtime_scoreboard.run(token=os.environ.get("D_TOKEN"))
