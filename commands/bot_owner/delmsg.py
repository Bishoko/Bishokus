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
from utils.sql import get_db_connection


async def delmsg_text(message: nextcord.Message):
    # Get the reply message
    reply = message.reference
    if reply:
        reply_message = await message.channel.fetch_message(reply.message_id)
        await reply_message.delete()
    await message.delete()
    

info = {
    "delmsg": {
        "category": "bot_owner",
        "aliases": ["removemsg", "supprçastp", "supprmsg"],
        "hidden_aliases": ["del_msg", "remove_msg", "suppr_ça_stp", "suppr_msg"],
        "available": ["text_command"],
        "visibility": "bot_owner",
        "user_permissions": ["bot_owner"],
        "name": "delmsg",
        "desc": "Deletes a replied message (BOT OWNER ONLY)",
        "args": []
    }
}

cmd = CmdLocale(list(info.keys())[0], get_commands_locales(info))

class DelMsgcog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

def setup(bot: commands.Bot):
    bot.add_cog(DelMsgcog(bot))

# Text command handler wrapper that adapts to message handler signature
@checks.owner_only()
async def _message_handler(bot, message: nextcord.Message, lang: str, guild_prefix: str):
    await delmsg_text(message)
