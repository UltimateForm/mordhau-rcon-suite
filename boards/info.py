import os
import discord
from discord.ext import tasks
from datetime import datetime, timezone
from common import logger, parsers

from common.compute import compute_time_txt
from rcon.rcon import RconClient

BOARD_REFRESH_TIME = int(os.environ.get("INFO_REFRESH_TIME", 30))


class InfoBoard(discord.Client):
    _channel_id: int = 0
    _channel: discord.TextChannel | None = None
    _current_message: discord.Message | None = None

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
        self.job.start()

    async def send_board(self):
        rcon_client = RconClient()
        await rcon_client.authenticate()
        server_info_raw = await rcon_client.execute("info")
        player_list_raw = await rcon_client.execute("playerlist")
        server_info = parsers.parse_server_info(server_info_raw)
        players = parsers.parse_playerlist(player_list_raw)
        players_text = (
            "\n".join([player.user_name for player in players])
            if len(players)
            else "No players online"
        )
        players_block = "```" + players_text + "```"
        current_time = round(datetime.now(timezone.utc).timestamp())
        time_sig = f"Last updated: <t:{current_time}> (<t:{current_time}:R>)"
        embed = discord.Embed(
            title=":clipboard: Server Info :clipboard:",
            description=time_sig,
            color=discord.Colour(3447003),
        )
        embed.add_field(name="Server Name", value=server_info.server_name)
        embed.add_field(name="Gamemode", value=server_info.game_mode)
        embed.add_field(name=f"Players ({len(players)})", value=players_block, inline=False)
        embed.set_footer(
            text=f"""
Updates every {compute_time_txt(BOARD_REFRESH_TIME/60)}
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
