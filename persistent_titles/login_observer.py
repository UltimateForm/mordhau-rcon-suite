import asyncio
from venv import logger
from reactivex import Observer
from common.models import LoginEvent
from persistent_titles.playtime_client import PlaytimeClient
from common.compute import compute_gate_text
from config_client.models import PtConfig
from rcon.rcon_pool import RconConnectionPool


class LoginObserver(Observer[LoginEvent | None]):
    _config: PtConfig
    playtime_client: PlaytimeClient | None
    _rcon_pool: RconConnectionPool

    def __init__(
        self,
        rcon_pool: RconConnectionPool,
        config: PtConfig,
        playtime_client: PlaytimeClient | None = None,
    ) -> None:
        self._config = config
        self.playtime_client = playtime_client
        self._rcon_pool = rcon_pool
        super().__init__()

    def get_tag(self, tag: str):
        return self._config.tag_format.format(tag)

    def get_rename(self, playfab_id: str):
        if not self._config.rename:
            return None
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
        client = await self._rcon_pool.get_client()
        try:
            await client.execute(f"renameplayer {playfab_id} {new_user_name}")
        except Exception as e:
            logger.info(
                f"[TitleCompute] Client {client.id} failed to send rcon renameplayer. Expiring client."
            )
            client.used = 120
            raise e
        finally:
            await self._rcon_pool.release_client(client)

    async def handle_salute(self, event_data: LoginEvent):
        playfab_id = event_data.player_id
        target_salute = self._config.salutes.get(playfab_id, None)
        if not target_salute:
            return
        await asyncio.sleep(
            self._config.salute_timer
        )  # so player can see his own salute
        client = await self._rcon_pool.get_client()
        try:
            await client.execute(f"say {target_salute}")
        except Exception as e:
            logger.info(
                f"[TitleCompute] Client {client.id} failed to send rcon say. Expiring client."
            )
            client.used = 120
            raise e
        finally:
            await self._rcon_pool.release_client(client)

    async def handle_rename(self, event_data: LoginEvent):
        playfab_id = event_data.player_id
        rename = self.get_rename(playfab_id)
        if not rename:
            return
        client = await self._rcon_pool.get_client()
        try:
            await client.execute(f"renameplayer {playfab_id} {rename}")
        except Exception as e:
            logger.info(
                f"[TitleCompute] Rcon client {client.id} failed to execute renameplayer, expiring client"
            )
            client.used = 120
            raise e
        finally:
            await self._rcon_pool.release_client(client)

    def on_next(self, event_data: LoginEvent | None) -> None:
        if not event_data:
            return
        order = event_data.instance.lower()
        if order == "out":
            return
        asyncio.create_task(self.handle_rename(event_data))
        asyncio.create_task(self.handle_salute(event_data))
        asyncio.create_task(self.handle_tag(event_data))
