import nextcord
from nextcord.ext import commands, application_checks
from nextcord.application_command import slash_command, message_command
from utils.get_commands_locales import get_commands_locales
from utils.locale_helpers import CmdLocale, get_slash_option
from utils import config, guild_only
from utils.settings.bot_ban import check_ban
from utils.languages import text
from utils.settings import prefix
from utils.settings.lang import get_lang

import utils.global_variables as gv
from utils.sql import get_db_connection


async def _toggle_wordplay(guild_id: int, lang: str):
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        
        # Update database with new data
        cursor.execute(
            "UPDATE guilds SET wordplay_enabled = !wordplay_enabled WHERE id = %s",
            (guild_id,)
        )
        connection.commit()
        
        # Fetch updated state
        cursor.execute(
            "SELECT wordplay_enabled FROM guilds WHERE id = %s",
            (guild_id,)
        )
        new_state = bool(cursor.fetchone()[0])
        
        # Send results
        if new_state:
            return text("toggle_wordplay_success_on", lang)
        else:
            return text("toggle_wordplay_success_off", lang)

    except:
        return text("toggle_wordplay_error", lang)
    
    finally:
        cursor.close()
        connection.close()


async def toggle_wordplay(lang: str, message: nextcord.Message):
    await message.reply(
        await _toggle_wordplay(message.guild.id, lang),
        mention_author=False
    )

async def toggle_wordplay_slash(lang: str, interaction: nextcord.Interaction):
    await interaction.response.send_message(
        await _toggle_wordplay(interaction.guild.id, lang)
    )


info = {
    "toggle_wordplay": {
        "category": "settings",
        "parent": "settings",
        "aliases": ["jdm"],
        "hidden_aliases": ["togglewordplay", "wordplaytoggle", "wordplay_toggle", "wordplayswitch", "wordplay_switch",
                           "jdmtoggle", "togglejdm", "jdm_toggle", "jdm_switch", "toggle_jdm", "switch_jdm",],
        "available": ["slash_command", "text_command"],
        "dm_available": False,
        "visibility": "everyone",
        "user_permissions": ["manage_guild"],
        "name": "toggle_wordplay_name",
        "desc": "toggle_wordplay_desc",
        "args": []
    },
}

cmd = CmdLocale(list(info.keys())[0], get_commands_locales(info))

parent = gv.get('bot').get_cog("SettingsCog").settings
class ToggleWordplayCog(commands.Cog):
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
    async def toggle_wordplay_command(self, interaction: nextcord.Interaction):
        await toggle_wordplay_slash(get_lang(interaction), interaction)


def setup(bot: commands.Bot):
    bot.add_cog(ToggleWordplayCog(bot))

# Text command handler wrapper that adapts to message handler signature
@guild_only()
async def _message_handler(bot, message: nextcord.Message, lang: str, prefix: str):
    await toggle_wordplay(lang, message)
