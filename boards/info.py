import asyncio
import aiofiles
import aiofiles.os
import discord
from discord.ext import tasks
from datetime import datetime, timezone
from common import logger, parsers
from common.compute import compute_time_txt
from common.discord import make_embed
from rcon.rcon import RconContext
from itertools import takewhile
from config_client.data import bot_config

BOARD_REFRESH_TIME = bot_config.info_refresh_time or 30


# TODO: create base class for these boards, too much duplication
class InfoBoard(discord.Client):
    _channel_id: int = 0
    _channel: discord.TextChannel | None = None
    _current_message: discord.Message | None = None
    file_path = "./persist/info_msg_id"

    def __init__(
        self,
        channel_id: int,
        intents: discord.Intents,
        **kwargs,
    ):
        self._channel_id = channel_id
        super().__init__(intents=intents, **kwargs)

    async def on_ready(self):
        logger.info(f"Retrieving info board channel {self._channel_id}")
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
            logger.error(f"InfoBoard: Error deleting existing board: {e}")

    async def send_board(self):
        try:
            server_info_raw: str = ""
            player_list_raw: str = ""
            async with asyncio.timeout(30):
                async with RconContext() as client:
                    server_info_raw = await client.execute("info")
                    player_list_raw = await client.execute("playerlist")
            server_info = parsers.parse_server_info(server_info_raw)
            players = parsers.parse_playerlist(player_list_raw)
            players_text = "" if len(players) > 0 else "No players online"
            for player in takewhile(lambda x: len(players_text) < 976, players):
                players_text += f"{player.player_id} - {player.user_name}\n"
            players_text = players_text.rstrip()
            players_text_len = len(players_text.splitlines())
            if players_text_len < len(players):
                players_text += "\n-- CUT SHORT FOR DISPLAY --"
            players_block = "```" + players_text + "```"
            current_time = round(datetime.now(timezone.utc).timestamp())
            time_sig = f"Last updated: <t:{current_time}> (<t:{current_time}:R>)"
            embed = make_embed(
                server_info.server_name,
                description=time_sig,
                color=discord.Colour(3447003),
                footer_txt=f"Updates every {compute_time_txt(BOARD_REFRESH_TIME/60)}",
            )
            embed.add_field(name="Gamemode", value=server_info.game_mode)
            embed.add_field(name="Map", value=server_info.map)
            embed.add_field(
                name=f"Players online: ({len(players)})", value=players_block, inline=False
            )
            if not self._current_message:
                self._current_message = await self._channel.send(embed=embed)
                asyncio.create_task(self.write_msg_id())
            else:
                await self._current_message.edit(embed=embed)
        except Exception as e:
            logger.error(f"Failed to update server info board {e}")

    @tasks.loop(seconds=BOARD_REFRESH_TIME)
    async def job(self):
        await self.send_board()
