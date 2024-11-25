import discord
import os

common_intents = discord.Intents.default()
common_intents.message_content = True


def make_embed(
    title: str,
    description: str | None = None,
    color: discord.Colour | None = None,
    footer_txt: str | None = None,
):
    footer_txt_env = os.environ.get(
        "EMBED_FOOTER_TXT",
        "Bot source: https://github.com/UltimateForm/mordhau-rcon-suite",
    )
    footer_icon = os.environ.get("EMBED_FOOTER_ICON", None)
    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_footer(
        text="\n".join([footer_txt, footer_txt_env]) if footer_txt else footer_txt_env,
        icon_url=footer_icon,
    )
    return embed
