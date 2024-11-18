import asyncio
from reactivex import Observer
from config_client.data import Config
from persistent_titles.compute import (
    compute_gate_text,
    compute_next_gate_text,
    compute_time_txt,
)
from rcon.rcon import RconContext
from persistent_titles.playtime_client import PlaytimeClient
from common.parsers import parse_chat_event


class ChatObserver(Observer[str]):
    playtime_client: PlaytimeClient
    _config: Config

    def __init__(self, config: Config, playtime_client: PlaytimeClient) -> None:
        self.playtime_client = playtime_client
        self._config = config
        super().__init__()

    async def handle_playtime(self, playfab_id: str, user_name: str):
        user_playtime = await self.playtime_client.get_playtime(playfab_id)
        full_msg = ""
        if user_playtime < 1:
            full_msg = f"{user_name} has no recorded playtime"
        else:
            unit = "mins" if user_playtime <= 60 else "hours"
            time = user_playtime if user_playtime < 60 else round(user_playtime / 60, 1)
            time_comp = f"{time} {unit}"
            user_comp = f"{user_name} has played"
            full_msg = " ".join([user_comp, time_comp])
        async with RconContext() as client:
            await client.execute(f"say {full_msg}")

    async def handle_rank(self, playfab_id: str, user_name: str):
        user_playtime = await self.playtime_client.get_playtime(playfab_id)
        global_rank = self._config.tags.get("*", None)
        full_msg = ""
        (_, rank_txt) = compute_gate_text(user_playtime, self._config.playtime_tags)
        full_msg += f"{user_name} rank: {rank_txt or global_rank}"
        (next_rank_minutes, next_rank_txt) = compute_next_gate_text(
            user_playtime, self._config.playtime_tags
        )
        if next_rank_txt is not None:
            full_msg += (
                f"; Next: {next_rank_txt} at {compute_time_txt(next_rank_minutes)}"
            )
        async with RconContext() as client:
            await client.execute(f"say {full_msg}")

    def on_next(self, value: str) -> None:
        event_data = parse_chat_event(value)
        if not event_data:
            return
        message = event_data.message
        playfab_id = event_data.player_id
        user_name = event_data.user_name
        if message == ".playtime":
            asyncio.create_task(self.handle_playtime(playfab_id, user_name))
        elif message == ".rank":
            asyncio.create_task(self.handle_rank(playfab_id, user_name))


# todo: add local test run here
