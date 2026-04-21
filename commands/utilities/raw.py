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


def _raw(input: str, everyone_permission: bool, lang: str) -> str:
    if input.replace(" ", "") == "":
        return text('raw_error_empty_msg', lang)
    
    if ("@everyone" in input or "@here" in input):  # and not everyone_permission:
        return f"```{input}```"
    
    return f"```{input}```\n{input}"


async def raw_text(lang: str, message: nextcord.Message):
    await message.reply(
        _raw(message.content, message.mention_everyone, lang),
        mention_author=False
    )

async def raw_slash(lang: str, interaction: nextcord.Interaction, input: str):
    await interaction.response.send_message(
        _raw(input, interaction.permissions.mention_everyone, lang),
        ephemeral=False
    )


info = {
    "raw": {
        "category": "utilities",
        "aliases": [],
        "hidden_aliases": ["brute", "brut", "dry", "naked", "écru", "cru", "crue", "crus"],
        "available": ["slash_command", "text_command"],
        "visibility": "everyone",
        "user_permissions": [],
        "name": "raw_name",
        "desc": "raw_desc",
        "args": [
            {
                "name": "raw_arg_name",
                "desc": "raw_arg_desc"
            }
        ]
    }
}

cmd = CmdLocale(list(info.keys())[0], get_commands_locales(info))

class RawCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @check_ban()
    @slash_command(
        name=cmd.name,
        description=cmd.description,
        name_localizations=cmd.name_localizations,
        description_localizations=cmd.description_localizations
    )
    async def raw_command(self, interaction: nextcord.Interaction,
        input: str = get_slash_option(cmd.arg(0))
    ):
        await raw_slash(get_lang(interaction), interaction, input)


def setup(bot: commands.Bot):
    bot.add_cog(RawCog(bot))

# Text command handler wrapper that adapts to message handler signature
async def _message_handler(bot, message: nextcord.Message, lang: str, guild_prefix: str):
    await raw_text(lang, message)
