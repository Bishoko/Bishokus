import nextcord
from nextcord.ext import commands, application_checks
from nextcord.application_command import slash_command, message_command
from utils.logger import log
from utils.get_commands_locales import get_commands_locales
from utils.locale_helpers import CmdLocale, get_slash_option
from utils import config
from utils.settings.bot_ban import check_ban
from utils.languages import text
from utils.settings import prefix
from utils.settings.lang import get_lang

import subprocess

BOT_NAME = "Bishokus"
BOT_OWNER = config.get("owner-contact-username")
BOT_CREATION_DATE = "17 Sep 2021"
BOT_LIBRARY = "nextcord"
BOT_VERSION = "rewrite"  # placeholder that will be replaced with git tag if available
BOT_THUMBNAIL_URL = config.get("bot-avatar-url")
BOT_PAGE_URL = config.get("bot-page-url")
BOT_GITHUB_URL = config.get("github-url")
SUPPORT_SERVER_URL = config.get("support-server-url")
INVITE_URL = config.get("invite-url")

def _get_and_format_version() -> str:
    # Get git tag
    try:
        version = subprocess.check_output(["git", "describe", "--tags"], stderr=subprocess.DEVNULL).decode().strip()
    except Exception as e:
        log.warning(f"Failed to get git tag: {e}")
        version = BOT_VERSION
    
    # Format version string
    if version == "rewrite":
        return version

    # Check if version is in format tag-commits-githash (e.g. v2.0.0-8-g5450b8d)
    splitted = version.split("-")
    if len(splitted) == 3 and splitted[1].isdigit() and splitted[2].startswith("g"):
        tag = splitted[0]
        commit = splitted[2][1:]
        return f"[{tag}]({BOT_GITHUB_URL}/releases/tag/{tag})[-{splitted[1]}-{commit}]({BOT_GITHUB_URL}/commit/{commit})"

    # If it's just a tag (e.g. v2.0.0), link to the release page
    return f"[{version}]({BOT_GITHUB_URL}/releases/tag/{version})"

BOT_VERSION = _get_and_format_version()


class InfoView(nextcord.ui.View):
    def __init__(self, lang: str):
        super().__init__()
        self.add_item(nextcord.ui.Button(
            label=text("info_invite_link", lang),
            url=INVITE_URL,
            style=nextcord.ButtonStyle.link
        ))
        self.add_item(nextcord.ui.Button(
            label=text("info_bot_page", lang),
            url=BOT_PAGE_URL,
            style=nextcord.ButtonStyle.link
        ))
        self.add_item(nextcord.ui.Button(
            label=text("info_support_server", lang),
            url=SUPPORT_SERVER_URL,
            style=nextcord.ButtonStyle.link
        ))
        self.add_item(nextcord.ui.Button(
            emoji="<:github:1499853061621944471>",
            url=BOT_GITHUB_URL,
            style=nextcord.ButtonStyle.link
        ))

def _build_info_embed(bot: commands.Bot, lang: str) -> nextcord.Embed:
    server_count = len(bot.guilds)
    user_count = sum(guild.member_count or 0 for guild in bot.guilds)
    channel_count = sum(len(guild.text_channels) for guild in bot.guilds)

    embed = nextcord.Embed(title=BOT_NAME, color=config.get("embed-color"))
    embed.set_thumbnail(url=BOT_THUMBNAIL_URL)

    embed.add_field(name=text("info_creator", lang), value=BOT_OWNER, inline=True)
    embed.add_field(name=text("info_creation_date", lang), value=BOT_CREATION_DATE, inline=True)
    # embed.add_field(name=text("info_library", lang), value=BOT_LIBRARY, inline=True)
    embed.add_field(name=text("info_version", lang), value=BOT_VERSION, inline=True)
    # embed.add_field(name=text("info_lines_of_code", lang), value=_count_python_lines(), inline=True)
    # embed.add_field(name="** **", value="** **", inline=True)
    # embed.add_field(name="** **", value="** **", inline=True)

    embed.add_field(name=text("info_server_count", lang), value=str(server_count), inline=True)
    embed.add_field(name=text("info_channel_count", lang), value=str(channel_count), inline=True)
    embed.add_field(name=text("info_user_count", lang), value=str(user_count), inline=True)

    return embed


async def info_text(bot: commands.Bot, lang: str, message: nextcord.Message):
    await message.reply(
        embed=_build_info_embed(bot, lang),
        view=InfoView(lang),
        mention_author=False
    )


async def info_slash(bot: commands.Bot, lang: str, interaction: nextcord.Interaction):
    await interaction.response.send_message(
        embed=_build_info_embed(bot, lang),
        view=InfoView(lang)
    )


info = {
    "info": {
        "category": "bot",
        "aliases": ["about", "bishokus"],
        "hidden_aliases": ["botinfo", "information", "informations", "stats", "statistics"],
        "available": ["slash_command", "text_command"],
        "visibility": "everyone",
        "user_permissions": [],
        "name": "info_name",
        "desc": "info_desc",
        "args": []
    }
}

cmd = CmdLocale(list(info.keys())[0], get_commands_locales(info))

class InfoCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @check_ban()
    @slash_command(
        name=cmd.name,
        description=cmd.description,
        name_localizations=cmd.name_localizations,
        description_localizations=cmd.description_localizations
    )
    async def info_command(self, interaction: nextcord.Interaction):
        await info_slash(self.bot, get_lang(interaction), interaction)


def setup(bot: commands.Bot):
    bot.add_cog(InfoCog(bot))

async def _message_handler(bot, message: nextcord.Message, lang: str, guild_prefix: str):
    await info_text(bot, lang, message)
