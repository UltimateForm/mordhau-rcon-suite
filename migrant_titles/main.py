import asyncio
from dataclasses import dataclass
from reactivex import Observable, Subject
from common.models import KillfeedEvent, PlayerStore
from config_client.data import pt_config, bot_config
from rcon.rcon_listener import RconListener
from rcon.rcon import RconContext
from common import logger

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
    _player_store: PlayerStore

    def __init__(self, player_store: PlayerStore):
        self.rex_tile = bot_config.title or DEFAULT_REX_TITLE
        self._player_store = player_store
        super().__init__()

    async def _execute_command(self, command: str):
        async with RconContext() as client:
            await client.execute(command)

    def _sanitize_name(self, playfab_id: str, current_name: str):
        login_username = self._player_store.players.get(playfab_id, None)
        rename = pt_config.rename.get(playfab_id, None)
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
            # elif killer_playfab_id == self.current_rex:
            #     self.current_rex = ""
            #     asyncio.create_task(
            #         self._execute_command(
            #             f"say {killer} has defeated {killed} and claimed his {self.rex_tile} title"
            #         )
            #     )
            #     self._remove_rex(killer_playfab_id, killer)
        except Exception as e:
            logger.error(f"Failed to process REX tag compute, {str(e)}")


class MigrantTitles:
    _killfeed_observable: Observable[KillfeedEvent]
    rex_compute: TitleCompute

    def __init__(
        self, killfeed_listener: Observable[KillfeedEvent], player_store: PlayerStore
    ):
        self._killfeed_observable = killfeed_listener
        self.rex_compute = TitleCompute(player_store)
        self._killfeed_observable.subscribe(self.rex_compute._process_killfeed_event)


async def main():
    login_listener = RconListener(event="login", listening=False)
    killfeed_listener = RconListener(event="killfeed", listening=False)
    MigrantTitles(killfeed_listener, login_listener)
    await asyncio.gather(killfeed_listener.start(), login_listener.start())


if __name__ == "__main__":
    asyncio.run(main())
