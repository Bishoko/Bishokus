import nextcord
from nextcord.ext import commands, application_checks
from nextcord.application_command import slash_command, message_command
from utils.get_commands_locales import get_commands_locales
from utils.locale_helpers import CmdLocale, get_slash_option
from utils import config
from utils.settings.bot_ban import check_ban
from utils.languages import text
from utils.settings import prefix, lang
get_lang = lang.get_lang

import utils.global_variables as gv


info = {
    "settings confess": {
        "category": "settings",
        "parent": "settings",
        "has_subcommands": True,
        "aliases": [],
        "hidden_aliases": ["confession", "confes"],
        "available": ["slash_command", "text_command"],
        "visibility": "everyone",
        "user_permissions": ["manage_guild"],
        "name": "settings_confess_name",
        "desc": "",
        "args": []
    },
}

cmd = CmdLocale(list(info.keys())[0], get_commands_locales(info))

parent = gv.get('bot').get_cog("SettingsCog").settings
class SettingsConfessCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @check_ban()
    @application_checks.has_permissions(**{perm: True for perm in cmd.user_permissions})
    @parent.subcommand(
        name=cmd.name,
        name_localizations=cmd.name_localizations,
    )
    async def settings_confess(self, interaction: nextcord.Interaction):
        pass
        

def setup(bot: commands.Bot):
    bot.add_cog(SettingsConfessCog(bot))
