from os import environ
import asyncio
from dataclasses import dataclass
from reactivex import Observable, Subject
from common.models import KillfeedEvent
from config_client.main import config
from rcon.rcon_listener import RconListener
from rcon.rcon import RconContext
from common import parsers, logger

DEFAULT_REX_TITLE = "REX"


@dataclass
class MigrantComputeEvent:
    event_type: str  # removed/placed
    playfab_id: str
    user_name: str


# doesn't really need to be a class....
# but i had a issue and i was too lazy
class TitleCompute(Subject[MigrantComputeEvent]):
    current_rex: str = ""
    rex_tile: str = ""
    users_map: dict[str, str] = {}

    def __init__(self):
        self.rex_tile = environ.get("TITLE", DEFAULT_REX_TITLE)
        super().__init__()

    async def _execute_command(self, command: str):
        async with RconContext() as client:
            await client.execute(command)

    def _sanitize_name(self, playfab_id: str, current_name: str):
        login_username = self.users_map.get(playfab_id, None)
        rename = config.rename.get(playfab_id, None)
        target_name = rename or login_username or current_name
        return target_name.replace(f"[{self.rex_tile}]", "").lstrip()

    def _remove_rex(self, playfab_id: str, user_name):
        target_name = self._sanitize_name(playfab_id, user_name)
        task = asyncio.create_task(
            self._execute_command(f"renameplayer {playfab_id} {target_name}")
        )

        def callback(_task: asyncio.Task):
            self.on_next(MigrantComputeEvent("removed", playfab_id, target_name))

        task.add_done_callback(callback)

    def _place_rex(self, playfab_id: str, user_name):
        target_name = self._sanitize_name(playfab_id, user_name)
        task = asyncio.create_task(
            self._execute_command(
                f"renameplayer {playfab_id} [{self.rex_tile}] {target_name}"
            ),
        )

        def callback(_task: asyncio.Task):
            self.on_next(MigrantComputeEvent("placed", playfab_id, target_name))

        task.add_done_callback(callback)

    def _process_killfeed_event(self, event_data: KillfeedEvent):
        try:
            killer = event_data.user_name
            killed = event_data.killed_user_name
            killer_playfab_id = event_data.killer_id
            killed_playfab_id = event_data.killed_id
            if not self.current_rex and killer_playfab_id:
                asyncio.create_task(
                    self._execute_command(
                        f"say {killer} has defeated {killed} and claimed the vacant {self.rex_tile} title"
                    )
                )
                self._place_rex(killer_playfab_id, killer)
                self.current_rex = killer_playfab_id
            elif killed_playfab_id and self.current_rex == killed_playfab_id:
                asyncio.create_task(
                    self._execute_command(
                        f"say {killer} has defeated {killed} and claimed his {self.rex_tile} title"
                    )
                )
                if killer_playfab_id:
                    self._place_rex(killer_playfab_id, killer)
                self._remove_rex(killed_playfab_id, killed)
                self.current_rex = killer_playfab_id
            elif (
                killer.rstrip().startswith(f"[{self.rex_tile}]")
                and killer_playfab_id
                and killer_playfab_id != self.current_rex
            ):
                # this is a bug, boy has REX in his name but isn't actually current rex
                self._remove_rex(killer_playfab_id, killer)
            # note: uncomment this for solo debug
            elif killer_playfab_id == self.current_rex:
                self.current_rex = ""
                asyncio.create_task(
                    self._execute_command(
                        f"say {killer} has defeated {killed} and claimed his {self.rex_tile} title"
                    )
                )
                self._remove_rex(killer_playfab_id, killer)
        except Exception as e:
            logger.error(f"Failed to process REX tag compute, {str(e)}")

    def process_killfeed_raw_event(self, event: str):
        logger.debug(f"EVENT: {event}")
        event_data = parsers.parse_killfeed_event(event)
        if event_data:
            self._process_killfeed_event(event_data)

    def process_login_raw_event(self, event: str):
        logger.debug(f"EVENT: {event}")
        event_data = parsers.parse_login_event(event)
        if not event_data:
            return

        event_order = event_data.instance
        if event_order == "out":
            logged_out_playfab_id = event_data.player_id
            if logged_out_playfab_id and logged_out_playfab_id in self.users_map.keys():
                self.users_map.pop(logged_out_playfab_id)
            if self.current_rex == logged_out_playfab_id:
                self.current_rex = ""
        else:
            playfab_id = event_data.player_id
            username = event_data.user_name
            if playfab_id and username:
                self.users_map[playfab_id] = username


class MigrantTitles:
    _login_observable: Observable[str]
    _killfeed_listener: RconListener
    rex_compute: TitleCompute

    def __init__(self, login_observable: Observable[str]):
        self._login_observable = login_observable
        self._killfeed_listener = RconListener(event="killfeed", listening=False)
        self.rex_compute = TitleCompute()
        self._killfeed_listener.subscribe(self.rex_compute.process_killfeed_raw_event)
        self._login_observable.subscribe(self.rex_compute.process_login_raw_event)

    async def start(self):
        await self._killfeed_listener.start()


async def start_migrant_titles(login_observable: Observable[str]):
    migrant_titles = MigrantTitles(login_observable)
    await migrant_titles.start()


async def main():
    login_listener = RconListener(event="login", listening=False)
    migrant_titles = MigrantTitles(login_listener)
    await asyncio.gather(login_listener.start(), migrant_titles.start())


if __name__ == "__main__":
    asyncio.run(main())
