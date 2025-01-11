import asyncio
from reactivex import Observer
from common.models import LoginEvent
from persistent_titles.playtime_client import PlaytimeClient
from common.compute import compute_gate_text
from config_client.models import PtConfig
from rcon.rcon import RconContext


class LoginObserver(Observer[LoginEvent]):
    _config: PtConfig
    playtime_client: PlaytimeClient | None

    def __init__(
        self, config: PtConfig, playtime_client: PlaytimeClient | None = None
    ) -> None:
        self._config = config
        self.playtime_client = playtime_client
        super().__init__()

    def get_tag(self, tag: str):
        return self._config.tag_format.format(tag)

    def get_rename(self, playfab_id: str):
        rename = self._config.rename.get(playfab_id, None)
        return rename

    async def handle_tag(self, event_data: LoginEvent):
        playfab_id = event_data.player_id
        user_name = self.get_rename(playfab_id) or event_data.user_name
        target_tag = self._config.tags.get(playfab_id, None)
        if target_tag is None and self.playtime_client is not None:
            minutes_played = await self.playtime_client.get_playtime(playfab_id)
            (_, gate_txt) = compute_gate_text(
                minutes_played, self._config.playtime_tags
            )
            target_tag = gate_txt
        if target_tag is None:
            target_tag = self._config.tags.get("*", None)
        if not target_tag:
            return
        tag_formatted = self.get_tag(target_tag)
        sanitized_username = user_name.replace(tag_formatted, "")
        new_user_name = " ".join([tag_formatted, sanitized_username])
        async with asyncio.timeout(10):
            async with RconContext() as client:
                await client.execute(f"renameplayer {playfab_id} {new_user_name}")

    async def handle_salute(self, event_data: LoginEvent):
        playfab_id = event_data.player_id
        target_salute = self._config.salutes.get(playfab_id, None)
        if not target_salute:
            return
        await asyncio.sleep(
            self._config.salute_timer
        )  # so player can see his own salute
        async with asyncio.timeout(10):
            async with RconContext() as client:
                await client.execute(f"say {target_salute}")

    async def handle_rename(self, event_data: LoginEvent):
        playfab_id = event_data.player_id
        rename = self.get_rename(playfab_id)
        if not rename:
            return
        async with asyncio.timeout(10):
            async with RconContext() as client:
                await client.execute(f"renameplayer {playfab_id} {rename}")

    def on_next(self, event_data: LoginEvent) -> None:
        if not event_data:
            return
        order = event_data.instance.lower()
        if order == "out":
            return
        asyncio.create_task(self.handle_rename(event_data))
        asyncio.create_task(self.handle_salute(event_data))
        asyncio.create_task(self.handle_tag(event_data))
