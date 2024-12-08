import asyncio
import random
from reactivex import Observer
from common.parsers import parse_killfeed_event
from common.compute import compute_gate
from config_client.data import ks_config
from config_client.models import KsConfig
from rcon.rcon import RconContext


def get_closest_multiple(n: int, factor: int):
    return round(factor * round(n / factor))


def get_template(streak: int, source: dict[str, str | list[str]]) -> str | None:
    target = source.get(str(streak), source.get("*", None))
    if type(target) is list:
        return random.choice(target)
    else:
        return target


class KillStreaks(Observer[str]):
    tally = dict[str, int]
    _config: KsConfig

    def __init__(self) -> None:
        self.tally = {}
        self._config = ks_config
        super().__init__()

    async def handle_killer_streak(self, user_name: str, playfabId: str):
        current_streak = self.tally.get(playfabId, 0)
        current_streak += 1
        self.tally[playfabId] = current_streak
        if current_streak > 0 and current_streak % 5 != 0:
            return
        closest_mult = get_closest_multiple(current_streak, 5)
        if current_streak != closest_mult:
            return
        template = get_template(current_streak, self._config.streak)
        if not template:
            return
        msg = template.format(user_name, current_streak)
        async with asyncio.timeout(10):
            async with RconContext() as client:
                await client.execute(f"say {msg}")

    async def handle_killed_streak(
        self, user_name: str, playfabId: str, killer_name: str
    ):
        current_streak = self.tally.pop(playfabId, 0)
        if current_streak < 5:
            return
        streak_gates = [int(key) for key in self._config.end.keys() if key.isnumeric()]
        template: str = self._config.end.get("*", None)
        if len(streak_gates) > 0:
            gate = compute_gate(current_streak, streak_gates)
            template = get_template(gate, self._config.end)
        if not template:
            return
        msg = template.format(killer_name, current_streak, user_name)
        async with asyncio.timeout(10):
            async with RconContext() as client:
                await client.execute(f"say {msg}")

    def on_next(self, raw: str):
        kill_event = parse_killfeed_event(raw)
        if kill_event is None:
            return
        asyncio.create_task(
            self.handle_killer_streak(kill_event.user_name, kill_event.killer_id)
        )
        asyncio.create_task(
            self.handle_killed_streak(
                kill_event.killed_user_name, kill_event.killed_id, kill_event.user_name
            )
        )
