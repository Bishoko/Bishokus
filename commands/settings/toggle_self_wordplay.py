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

from utils.vip import vip_command
import utils.global_variables as gv
from utils.sql import get_db_connection


async def _toggle_self_wordplay(user_id: int, lang: str):
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        
        # Update database with new data
        cursor.execute(
            "UPDATE users SET wordplay_enabled = !wordplay_enabled WHERE id = %s",
            (user_id,)
        )
        connection.commit()
        
        # Fetch updated state
        cursor.execute(
            "SELECT wordplay_enabled FROM users WHERE id = %s",
            (user_id,)
        )
        new_state = bool(cursor.fetchone()[0])
        
        # Send results
        if new_state:
            return text("toggle_self_wordplay_success_on", lang)
        else:
            return text("toggle_self_wordplay_success_off", lang)

    except:
        return text("toggle_self_wordplay_error", lang)
    
    finally:
        cursor.close()
        connection.close()


async def toggle_self_wordplay(lang: str, message: nextcord.Message):
    await message.reply(
        await _toggle_self_wordplay(message.author.id, lang),
        mention_author=False
    )

async def toggle_self_wordplay_slash(lang: str, interaction: nextcord.Interaction):
    await interaction.response.send_message(
        await _toggle_self_wordplay(interaction.user.id, lang)
    )


info = {
    "toggle_self_wordplay": {
        "category": "settings",
        "parent": "settings",
        "aliases": ["selfjdm"],
        "hidden_aliases": ["self_jdm", "jdm_self",
                           "toggleselfwordplay", "wordplayselftoggle", "wordplaytoggleself", "togglewordplayself",
                           "switchselfwordplay", "wordplayselfswitch", "wordplayswitchself", "switchwordplayself",
                           "toggle_self_wordplay", "wordplay_self_toggle", "wordplay_toggle_self", "toggle_wordplay_self",
                           "switch_self_wordplay", "wordplay_self_switch", "wordplay_switch_self", "switch_wordplay_self",
                           
                           "toggleselfjdm", "jdmselftoggle", "jdmtoggleself", "togglejdmself",
                           "switchselfjdm", "jdmselfswitch", "jdmswitchself", "switchjdmself",
                           "toggle_self_jdm", "jdm_self_toggle", "jdm_toggle_self", "toggle_jdm_self",
                           "switch_self_jdm", "jdm_self_switch", "jdm_switch_self", "switch_jdm_self",
                           ],
        "available": ["slash_command", "text_command"],
        "dm_available": False,
        "visibility": "everyone",
        "user_permissions": ["manage_guild"],
        "name": "toggle_self_wordplay_name",
        "desc": "toggle_self_wordplay_desc",
        "args": []
    },
}

cmd = CmdLocale(list(info.keys())[0], get_commands_locales(info))

parent = gv.get('bot').get_cog("SettingsCog").settings
class ToggleSelfWordplayCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @check_ban()
    @guild_only()
    @vip_command()
    @parent.subcommand(
        name=cmd.name,
        description=cmd.description,
        name_localizations=cmd.name_localizations,
        description_localizations=cmd.description_localizations,
    )
    async def toggle_self_wordplay_command(self, interaction: nextcord.Interaction):
        await toggle_self_wordplay_slash(get_lang(interaction), interaction)


def setup(bot: commands.Bot):
    bot.add_cog(ToggleSelfWordplayCog(bot))

# Text command handler wrapper that adapts to message handler signature
@guild_only()
@vip_command()
async def _message_handler(bot, message: nextcord.Message, lang: str, prefix: str):
    await toggle_self_wordplay(lang, message)
