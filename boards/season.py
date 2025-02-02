import asyncio
import discord
from motor.motor_asyncio import (
    AsyncIOMotorCollection,
)
from table2ascii import table2ascii as t2a
from boards.base import Board
from config_client.data import bot_config
from common.discord import make_season_embed
from config_client.models import SeasonConfig
from seasons.season_controller import SEASON_TOPIC, SeasonEvent
from common import logger
from common.compute import compute_time_txt
from rank_compute.kills import update_achieved_ranks

BOARD_REFRESH_TIME = bot_config.kills_refresh_time or 60


class SeasonScoreboard(Board):
    _kills_collection: AsyncIOMotorCollection | None
    _season_cfg: SeasonConfig | None = None
    _discord_client: discord.Client | None = None

    @property
    def file_path(self) -> str:
        return "./persist/season_msg_id"

    @property
    def active(self) -> bool:
        return self._season_cfg and self._season_cfg.is_active

    def __init__(
        self,
        kills_collection: AsyncIOMotorCollection,
        time_interval=60,
        initial_season: SeasonConfig | None = None,
    ):
        self._season_cfg = initial_season
        self._kills_collection = kills_collection
        SEASON_TOPIC.subscribe(lambda x: asyncio.create_task(self.season_next(x)))
        super().__init__(
            initial_season.channel if initial_season and initial_season.channel else 0,
            time_interval,
        )

    def on_next(self, client: discord.Client):
        self._discord_client = client
        asyncio.create_task(self.start(client))

    async def load_channel(self, client: discord.Client):
        self._channel = await client.fetch_channel(self._channel_id)

    async def start(self, client: discord.Client):
        if not self.active:
            logger.info(
                f"{self.__class__.__name__}: Ignoring board startup as season is not active"
            )
            return
        logger.info(
            f"{self.__class__.__name__}: Retrieving discord channel {self._channel_id}"
        )
        await self.load_channel(client)
        await self.delete_previous_message()
        self.job.cancel()
        self.job.start()

    async def season_next(self, event: SeasonEvent):
        self._season_cfg = await SeasonConfig.aload()
        if event == SeasonEvent.END:
            self.job.stop()
            self._channel = None
            self._current_message = None
            await self.destroy_msg_id()
            return
        elif event == SeasonEvent.START:
            if not self._discord_client:
                logger.info(
                    f"{self.__class__.__name__}: Season started but no client available yet"
                )
                return
            await self.start(self._discord_client)

    def compute_kdr(self, record: dict) -> list[str]:
        user_name = record.get("user_name", None) or record.get(
            "playfab_id", "<UNKNOWN>"
        )
        season_dict = record.get("season", {}).get(self._season_cfg.name, {})
        kill_count = season_dict.get("kill_count", 0)
        death_count = season_dict.get("death_count", 0)
        ratio = str(round(kill_count / death_count, 2)) if death_count > 0 else "-"
        if len(user_name) > 26:
            user_name = user_name[:24] + ".."
        return [user_name, kill_count, death_count, ratio]

    async def update_achieved_ranks(self, records: dict):
        if not self._season_cfg:
            # just in case....
            return
        inf = float("inf")
        await update_achieved_ranks(
            [
                {"playfab_id": item["playfab_id"], "rank": index + 1}
                for (index, item) in enumerate(records)
                if item.get("achiev", {}).get(self._season_cfg.name, inf) > index + 1
            ],
            self._kills_collection,
            self._season_cfg,
        )

    async def send_board(self):
        if not self._season_cfg or not self._season_cfg.is_active:
            return
        top_20_items: list[dict] = (
            await self._kills_collection.find()
            .sort(f"season.{self._season_cfg.name}.kill_count", -1)
            .limit(20)
            .to_list()
        )
        asyncio.create_task(self.update_achieved_ranks(top_20_items))
        ascii_table = (
            "```"
            + t2a(
                header=["Rank", "Username", "K", "D", "R"],
                body=[
                    [index + 1, *self.compute_kdr(item)]
                    for (index, item) in enumerate(top_20_items)
                ],
            )
            + "```"
        )
        embed = make_season_embed(self._season_cfg)
        embed.description = embed.description + "\n" + ascii_table
        embed.set_footer(
            text=f"Updates every {compute_time_txt(self._time_interval_mins)}"
            + "\n"
            + embed.footer.text,
            icon_url=embed.footer.icon_url,
        )
        if not self._current_message:
            self._current_message = await self._channel.send(embed=embed)
            asyncio.create_task(self.write_msg_id())
        else:
            await self._current_message.edit(embed=embed)
