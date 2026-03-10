import nextcord
from nextcord.ext import commands, application_checks
from nextcord.application_command import slash_command, message_command
from utils.logger import log
from utils.get_commands_locales import get_commands_locales
from utils.locale_helpers import CmdLocale, get_slash_option
from utils import config, guild_only
from utils.settings.bot_ban import check_ban
from utils.languages import text
from utils.settings import prefix
from utils.settings.lang import get_lang

import utils.global_variables as gv
from utils.sql import get_db_connection

# TODO: remove this command to add a general "/toggle <command>"" command, toggling snipe will still disable logging


async def _toggle_snipe(guild_id: int, lang: str):
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        
        # Update database with new data
        cursor.execute(
            "UPDATE guilds SET sniper_enabled = !sniper_enabled WHERE id = %s",
            (guild_id,)
        )
        connection.commit()
        
        # Fetch updated state
        cursor.execute(
            "SELECT sniper_enabled FROM guilds WHERE id = %s",
            (guild_id,)
        )
        new_state = bool(cursor.fetchone()[0])
        
        # Send results
        if new_state:
            return text("toggle_snipe_success_on", lang)
        else:
            return text("toggle_snipe_success_off", lang)

    except:
        return text("toggle_snipe_error", lang)
    
    finally:
        cursor.close()
        connection.close()


async def toggle_snipe(lang: str, message: nextcord.Message):
    await message.reply(
        await _toggle_snipe(message.guild.id, lang),
        mention_author=False
    )

async def toggle_snipe_slash(lang: str, interaction: nextcord.Interaction):
    await interaction.response.send_message(
        await _toggle_snipe(interaction.guild.id, lang)
    )


info = {
    "toggle_snipe": {
        "category": "settings",
        "parent": "settings",
        "aliases": [],
        "hidden_aliases": ["togglesnipe", "snipetoggle", "snipe_toggle", "snipeswitch", "snipe_switch",
                           "togglesniper", "snipertoggle", "sniper_toggle", "sniperswitch", "sniper_switch",],
        "available": ["slash_command", "text_command"],
        "dm_available": False,
        "visibility": "everyone",
        "user_permissions": ["manage_guild"],
        "name": "toggle_snipe_name",
        "desc": "toggle_snipe_desc",
        "args": []
    },
}

cmd = CmdLocale(list(info.keys())[0], get_commands_locales(info))

parent = gv.get('bot').get_cog("SettingsCog").settings
class ToggleSnipeCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @check_ban()
    @guild_only()
    @parent.subcommand(
        name=cmd.name,
        description=cmd.description,
        name_localizations=cmd.name_localizations,
        description_localizations=cmd.description_localizations,
    )
    async def toggle_snipe_command(self, interaction: nextcord.Interaction):
        await toggle_snipe_slash(get_lang(interaction), interaction)


def setup(bot: commands.Bot):
    bot.add_cog(ToggleSnipeCog(bot))

# Text command handler wrapper that adapts to message handler signature
@guild_only()
async def _message_handler(bot, message: nextcord.Message, lang: str, prefix: str):
    await toggle_snipe(lang, message)
