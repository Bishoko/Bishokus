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


BOT_OWNER = config.get("owner-contact-username")
BOT_OWNER_EMAIL = config.get("owner-contact-email")
BOT_PAGE_URL = config.get("bot-page-url")
SUPPORT_SERVER_URL = config.get("support-server-url")
INVITE_URL = config.get("invite-url")


def _build_support_embed(lang: str) -> nextcord.Embed:
    description = text("support_server", lang).replace("%support_server_url%", SUPPORT_SERVER_URL)
    description += "\n" + text("support_owner_dm", lang).replace("%owner_contact_discord%", BOT_OWNER)
    description += "\n" + text("support_owner_email", lang).replace("%owner_contact_email%", BOT_OWNER_EMAIL)

    embed = nextcord.Embed(
        title=text("support_embed_title", lang),
        description=description,
        color=config.get("embed-color")
    )

    return embed


async def support_text(lang: str, message: nextcord.Message):
    await message.reply(
        SUPPORT_SERVER_URL,
        embed=_build_support_embed(lang),
        mention_author=False
    )


async def support_slash(lang: str, interaction: nextcord.Interaction):
    await interaction.response.send_message(
        SUPPORT_SERVER_URL,
        embed=_build_support_embed(lang)
    )


info = {
    "support": {
        "category": "bot",
        "aliases": [],
        "hidden_aliases": ["dm", "contact", "botsupport", "supportinfo", "supportinfos", "supportinformation", "supportinformations"],
        "available": ["slash_command", "text_command"],
        "visibility": "everyone",
        "user_permissions": [],
        "name": "support_name",
        "desc": "support_desc",
        "args": []
    }
}

cmd = CmdLocale(list(info.keys())[0], get_commands_locales(info))

class SupportCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @check_ban()
    @slash_command(
        name=cmd.name,
        description=cmd.description,
        name_localizations=cmd.name_localizations,
        description_localizations=cmd.description_localizations
    )
    async def support_command(self, interaction: nextcord.Interaction):
        await support_slash(get_lang(interaction), interaction)


def setup(bot: commands.Bot):
    bot.add_cog(SupportCog(bot))

async def _message_handler(bot, message: nextcord.Message, lang: str, guild_prefix: str):
    await support_text(lang, message)
