import asyncio
from datetime import timezone, datetime
from itertools import takewhile
from boards.base import Board
from common import logger, parsers
from common.compute import compute_time_txt
from common.discord import make_embed
from rcon.rcon import RconContext
import discord


class InfoBoard(Board):

    @property
    def file_path(self) -> str:
        return "./persist/info_msg_id"

    async def send_board(self):
        try:
            if not self._channel:
                raise ValueError(
                    "{self.__class__.__name__}: Channel {self._channel_id} not loaded"
                )
            server_info_raw: str = ""
            player_list_raw: str = ""
            async with asyncio.timeout(30):
                async with RconContext() as client:
                    server_info_raw = await client.execute("info")
                    player_list_raw = await client.execute("playerlist")
            server_info = parsers.parse_server_info(server_info_raw)
            if not server_info:
                raise ValueError(f"Failed to parse server info: {server_info_raw}")
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
                description="\n".join([time_sig, self.announcement]),
                color=discord.Colour(3447003),
                footer_txt=f"Updates every {compute_time_txt(self._time_interval_mins)}",
            )
            num_players_onlines = len(players)
            players_online = f"Players online: {num_players_onlines}"
            await self._client.change_presence(
                activity=discord.Activity(
                    type=discord.ActivityType.watching,
                    name=f"{num_players_onlines} players online",
                )
            )
            embed.add_field(name="Gamemode", value=server_info.game_mode)
            embed.add_field(name="Map", value=server_info.map)
            embed.add_field(
                name=players_online,
                value=players_block,
                inline=False,
            )
            if not self._current_message:
                self._current_message = await self._channel.send(embed=embed)
                asyncio.create_task(self.write_msg_id())
            else:
                await self._current_message.edit(embed=embed)
        except Exception as e:
            logger.error(f"Failed to update server info board {e}")
