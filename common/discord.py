import discord
from config_client.data import bot_config

common_intents = discord.Intents.default()
common_intents.message_content = True


def make_embed(
    title: str,
    description: str | None = None,
    color: discord.Colour | None = None,
    footer_txt: str | None = None,
):
    footer_txt_env = bot_config.embed_footer_txt or ""
    footer_icon = bot_config.embed_footer_icon
    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_footer(
        text="\n".join([footer_txt, footer_txt_env]) if footer_txt else footer_txt_env,
        icon_url=footer_icon,
    )
    return embed
