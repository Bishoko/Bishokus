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

from utils.sql.db_utils import backup_database
import io
import time


async def backupdb_text(message: nextcord.Message):
    # Backups the whole SQL database and sends it to the user. (BOT OWNER ONLY)
    # The backup needs to be restored later using the restoredb command.
    try:
        conn = get_db_connection()
        db_name = conn.database
        conn.close()

        sql_content = backup_database(db_name)

        backup_filename = f"backup_{db_name}_{int(time.time())}.sql"
        sql_bytes = sql_content.encode('utf-8')
        await message.channel.send(file=nextcord.File(io.BytesIO(sql_bytes), filename=backup_filename))

    except Exception as e:
        log.debug(f"Error in backupdb_text: {e}")
        await message.channel.send("An error occurred while trying to backup the database.")


info = {
    "backupdb": {
        "category": "bot_owner",
        "aliases": [],
        "hidden_aliases": [],
        "available": ["text_command"],
        "visibility": "bot_owner",
        "user_permissions": ["bot_owner"],
        "name": "backupdb",
        "desc": "Backups the whole SQL database and sends it to the user. (BOT OWNER ONLY)",
        "args": []
    }
}

cmd = CmdLocale(list(info.keys())[0], get_commands_locales(info))

class BackupDBcog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

def setup(bot: commands.Bot):
    bot.add_cog(BackupDBcog(bot))

# Text command handler wrapper that adapts to message handler signature
@checks.owner_only()
async def _message_handler(bot, message: nextcord.Message, lang: str, guild_prefix: str):
    await backupdb_text(message)
