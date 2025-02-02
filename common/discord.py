import discord
from reactivex import Subject
from config_client.data import bot_config
from config_client.models import SeasonConfig
from datetime import datetime, timezone

common_intents = discord.Intents.default()
common_intents.message_content = True


def make_embed(
    title: str,
    description: str | None = None,
    color: discord.Colour | None = None,
    footer_txt: str | None = None,
):

    footer_txt_env = (
        bot_config.embed_footer_txt
        or "Bot source: https://github.com/UltimateForm/mordhau-rcon-suite"
    )
    footer_icon = bot_config.embed_footer_icon
    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_footer(
        text="\n".join([footer_txt, footer_txt_env]) if footer_txt else footer_txt_env,
        icon_url=footer_icon,
    )
    return embed


def make_season_embed(season_config: SeasonConfig):
    current_time = round(datetime.now(timezone.utc).timestamp())
    description = f"Last updated: <t:{current_time}> (<t:{current_time}:R>)"
    if season_config.embed_config.description:
        description = season_config.embed_config.description + "\n" + description
    embed = make_embed(
        title=season_config.embed_config.title or season_config.name,
        description=description,
        footer_txt=season_config.embed_config.footer_txt or None,
    )
    embed.color = 15844367
    if season_config.embed_config.image_url:
        embed.set_image(url=season_config.embed_config.image_url)
    return embed


class ObservableDiscordClient(discord.Client, Subject[discord.Client]):
    def __init__(self, intents: discord.Intents):
        discord.Client.__init__(self, intents=intents)
        Subject.__init__(self)

    async def on_ready(self):
        self.on_next(self)
        self.on_completed()
