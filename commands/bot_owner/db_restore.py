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

from utils.sql.db_utils import restore_database
import os


async def restoredb_text(message: nextcord.Message):
    # Restores the database from a backup file. (BOT OWNER ONLY)
    # The backup file should be sent as an attachment in the message.
    try:
        if not message.attachments:
            await message.channel.send("Please attach a backup file to restore the database.")
            return

        backup_file = message.attachments[0]

        backup_file_path = f".logs/{backup_file.filename}"
        await backup_file.save(backup_file_path)

        conn = get_db_connection()
        db_name = conn.database
        conn.close()

        with open(backup_file_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()

        restore_database(db_name, sql_content)

        await message.channel.send("Database restored successfully.")

        os.remove(backup_file_path)
    except Exception as e:
        log.debug(f"Error in restoredb_text: {e}")
        await message.channel.send("An error occurred while trying to restore the database.")

info = {
    "restoredb": {
        "category": "bot_owner",
        "aliases": [],
        "hidden_aliases": [],
        "available": ["text_command"],
        "visibility": "bot_owner",
        "user_permissions": ["bot_owner"],
        "name": "restoredb",
        "desc": "Restores the database from a backup file. (BOT OWNER ONLY)",
        "args": []
    }
}

cmd = CmdLocale(list(info.keys())[0], get_commands_locales(info))

class RestoreDBcog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

def setup(bot: commands.Bot):
    bot.add_cog(RestoreDBcog(bot))

# Text command handler wrapper that adapts to message handler signature
@checks.owner_only()
async def _message_handler(bot, message: nextcord.Message, lang: str, guild_prefix: str):
    await restoredb_text(message)
