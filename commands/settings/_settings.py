import nextcord
from nextcord.ext import commands, application_checks
from nextcord.application_command import slash_command, message_command
from utils.logger import log
from utils.get_commands_locales import get_commands_locales
from utils.locale_helpers import CmdLocale, get_slash_option
from utils import config, checks
from utils.settings.bot_ban import check_ban
from utils.languages import text
from utils.settings import prefix
from utils.settings.lang import get_lang


info = {
    "settings": {
        "category": "settings",
        "has_subcommands": True,
        "aliases": ["config"],
        "hidden_aliases": ["configuration", "setup", "options", "option", "prefs", "pref", "preferences", "preference", "setting"],
        "available": ["slash_command", "text_command"],
        "dm_available": False,
        "visibility": "everyone",
        "user_permissions": ["manage_guild"],
        "name": "settings_name",
        "desc": "",
        "args": []
    },
}

cmd = CmdLocale(list(info.keys())[0], get_commands_locales(info))

class SettingsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @check_ban()
    @checks.guild_only()
    @checks.user_permissions(manage_guild=True)
    @slash_command(
        name=cmd.name,
        name_localizations=cmd.name_localizations,
        default_member_permissions=(nextcord.Permissions(manage_guild=True))  # Only for parent command
    )
    async def settings(self, interaction: nextcord.Interaction):
        pass
        

def setup(bot: commands.Bot):
    bot.add_cog(SettingsCog(bot))
