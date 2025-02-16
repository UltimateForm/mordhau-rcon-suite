import asyncio
import random
from reactivex import Observer
from common.compute import compute_gate
from config_client.data import ks_config
from config_client.models import KsConfig
from rcon.rcon import RconContext
from common.models import KillfeedEvent


def get_closest_multiple(n: int, factor: int):
    return round(factor * round(n / factor))


def get_template(streak: int, source: dict[str, str | list[str]]) -> str | None:
    target = source.get(str(streak), source.get("*", None))
    if type(target) is list:
        return random.choice(target)
    else:
        return target  # type: ignore


class KillStreaks(Observer[KillfeedEvent | None]):
    tally: dict[str, int]
    _first_blood_claimed = False
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
        template: str | None | list[str] = self._config.end.get("*", None)
        if len(streak_gates) > 0:
            gate = compute_gate(current_streak, streak_gates)
            template = (
                get_template(gate, self._config.end) if gate is not None else None
            )
        if not template:
            return
        if type(template) is list:
            template = random.choice(template)
        msg = template.format(killer_name, current_streak, user_name)  # type: ignore
        async with asyncio.timeout(10):
            async with RconContext() as client:
                await client.execute(f"say {msg}")

    def reset(self):
        self.tally = {}
        self._first_blood_claimed = False

    async def self_end_ks(self, user_name: str, playfab_id: str):
        current_streak = self.tally.pop(playfab_id, 0)
        streak_gates = [
            int(key) for key in self._config.streak.keys() if key.isnumeric()
        ]
        if current_streak < min(streak_gates or [5]):
            return
        async with asyncio.timeout(10):
            async with RconContext() as client:
                await client.execute(
                    f"say {user_name} ended their own killstreak of {current_streak}"
                )

    async def first_blood(self, user_name: str, victim_name: str):
        if self._first_blood_claimed:
            return
        self._first_blood_claimed = True
        template = self._config.firstblood
        msg = template.format(user_name, 1, victim_name)
        async with asyncio.timeout(10):
            async with RconContext() as client:
                await client.execute(f"say {msg}")

    def on_next(self, kill_event: KillfeedEvent | None):
        if kill_event is None or not kill_event.killed_id or not kill_event.killer_id:
            return
        asyncio.create_task(
            self.first_blood(kill_event.user_name, kill_event.killed_user_name)
        )
        asyncio.create_task(
            self.handle_killer_streak(kill_event.user_name, kill_event.killer_id)
        )
        asyncio.create_task(
            self.handle_killed_streak(
                kill_event.killed_user_name, kill_event.killed_id, kill_event.user_name
            )
        )
