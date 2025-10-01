from xmlrpc.client import Boolean
import discord
from motor.motor_asyncio import (
    AsyncIOMotorCollection,
)
from table2ascii import table2ascii as t2a
from boards.base import Board
from common.gc_shield import backtask
from config_client.data import bot_config
from common.discord import make_season_embed
from config_client.models import SeasonConfig
from seasons.season_controller import SEASON_TOPIC, SeasonEvent
from common import logger
from common.compute import compute_time_txt

BOARD_REFRESH_TIME = bot_config.kills_refresh_time or 60


class SeasonScoreboard(Board):
    _kills_collection: AsyncIOMotorCollection
    _season_cfg: SeasonConfig | None = None

    @property
    def file_path(self) -> str:
        return "./persist/season_msg_id"

    @property
    def active(self) -> bool:
        return Boolean(self._season_cfg) and self._season_cfg.is_active  # type: ignore

    @property
    def season_name(self) -> str:
        return self._season_cfg.name if self._season_cfg else ""

    def __init__(
        self,
        client: discord.Client,
        kills_collection: AsyncIOMotorCollection,
        time_interval: int | None = 60,
        initial_season: SeasonConfig | None = None,
    ):
        self._season_cfg = initial_season
        self._kills_collection = kills_collection

        def launch_season_next(event: SeasonEvent):
            backtask(self.season_next(event))

        SEASON_TOPIC.subscribe(launch_season_next)
        super().__init__(
            client,
            initial_season.channel if initial_season and initial_season.channel else 0,
            time_interval,
        )

    async def start(self, bot: discord.Client):
        if not self.active:
            logger.info(
                f"{self.__class__.__name__}: Ignoring board startup as season is not active"
            )
            return
        logger.info(
            f"{self.__class__.__name__}: Retrieving discord channel {self._channel_id}"
        )
        await self.load_channel(bot)
        await self.delete_previous_message()
        self.job.cancel()
        self.job.start()

    async def season_next(self, event: SeasonEvent):
        self._season_cfg = await SeasonConfig.aload()
        self._channel_id = self._season_cfg.channel or 0 if self._season_cfg else 0
        if event == SeasonEvent.END:
            self.job.stop()
            self._channel = None
            self._current_message = None
            await self.destroy_msg_id()
            return
        elif event == SeasonEvent.START:
            if not self._client:
                logger.info(
                    f"{self.__class__.__name__}: Season started but no client available yet"
                )
                return
            await self.start(self._client)

    def compute_kdr(self, record: dict) -> list[str]:
        user_name = record.get("user_name", None) or record.get(
            "playfab_id", "<UNKNOWN>"
        )
        season_dict = record.get("season", {}).get(self.season_name, {})
        kill_count = season_dict.get("kill_count", 0)
        death_count = season_dict.get("death_count", 0)
        ratio = str(round(kill_count / death_count, 2)) if death_count > 0 else "-"
        if len(user_name) > 26:
            user_name = user_name[:24] + ".."
        return [user_name, kill_count, death_count, ratio]

    async def send_board(self):
        if not self._channel:
            raise ValueError(
                f"{self.__class__.__name__}: Channel {self._channel_id} not loaded"
            )
        if not self._season_cfg or not self._season_cfg.is_active:
            return
        top_20_items: list[dict] = (
            await self._kills_collection.find(
                {f"season.{self._season_cfg.name}": {"$exists": True}}
            )
            .sort(f"season.{self._season_cfg.name}.kill_count", -1)
            .limit(20)
            .to_list()
        )
        ascii_table = "```No players have played this season```"
        if len(top_20_items):
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
        embed.description = (
            embed.description + "\n" + ascii_table if embed.description else ascii_table
        )
        footer_txt: str = f"Updates every {compute_time_txt(self._time_interval_mins)}"
        embed.set_footer(
            text=(
                footer_txt + "\n" + embed.footer.text
                if embed.footer and embed.footer.text
                else footer_txt
            ),
            icon_url=embed.footer.icon_url if embed.footer else None,
        )
        if not self._current_message:
            self._current_message = await self._channel.send(embed=embed)
            backtask(self.write_msg_id())
        else:
            await self._current_message.edit(embed=embed)
