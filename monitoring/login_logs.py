from reactivex import Observer, Observable
import discord
from common.gc_shield import backtask
from common.models import LoginEvent
from config_client.models import BotConfig


class LoginLogs(Observer[LoginEvent | None]):
    _dc_client: discord.Client
    _channel: discord.abc.Messageable | None = None
    _channel_id: int = 0
    _allowed_mentions: discord.AllowedMentions

    def __init__(
        self,
        observable_dc_client: Observable[discord.Client],
        bot_config: BotConfig,
    ):
        if not bot_config.login_logs_channel:
            raise ValueError(
                "LoginLogs instantiated without actual channel to send logs to"
            )

        def launch_discord_ready(x: discord.Client):
            backtask(self._on_discord_ready(x))

        observable_dc_client.subscribe(launch_discord_ready)
        self._channel_id = bot_config.login_logs_channel
        self._allowed_mentions = discord.AllowedMentions(roles=True)
        super().__init__()

    async def _on_discord_ready(self, dc_client: discord.Client):
        self._dc_client = dc_client
        channel = await self._dc_client.fetch_channel(self._channel_id)
        if isinstance(channel, discord.abc.Messageable):
            self._channel = channel

    async def send_login_log(self, login_event: LoginEvent):
        if self._channel is None or login_event is None:
            return
        escaped_user_name = discord.utils.escape_markdown(login_event.user_name)
        escaped_id = discord.utils.escape_markdown(login_event.player_id)
        scribe_link = f"https://mordhau-scribe.com/player/{escaped_id}"

        event_name = "LOGIN" if login_event.instance.lower() == "in" else "LOGOUT"
        msg = f"**{escaped_user_name}** ([{escaped_id}]({scribe_link})) {event_name} {login_event.date}"
        await self._channel.send(msg)

    def on_next(self, value: LoginEvent | None):
        if value is None:
            return
        backtask(self.send_login_log(value))
