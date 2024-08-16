import json
import nextcord
from nextcord.ext import commands, application_checks
from utils.get_commands_locales import get_commands_locales

from commands.fun.ratio import ratio_context

from utils.settings import prefix, lang
from utils.settings.bot_ban import check_ban

# Load JSON localization data
with open('config/config.json', 'r', encoding='utf-8') as config_file:
    config = json.load(config_file)
    default_locale = config['default-slash-locale']


def get_lang(interaction: nextcord.Interaction) -> str:
    return lang.get_lang(interaction)


def register_context_menu_commands(bot: commands.Bot):
    locales = get_commands_locales()
    
    
    #  -- FUN --
    
    command = 'ratio'
    @bot.message_command(
        name=locales[command]['name'][default_locale],
        name_localizations=locales[command]['name']
    )
    @check_ban()
    async def ratio_context_command(interaction: nextcord.Interaction, message: nextcord.Message):
        await ratio_context(get_lang(interaction), interaction, message)

