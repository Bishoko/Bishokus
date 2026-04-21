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

import json
from datetime import datetime
from utils.sql import get_db_connection


async def _antisnipe(lang: str, user_id: int, guild_id: int, channel_id: int):
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        channel_id_str = str(channel_id)
        user_id_str = str(user_id)
        
        # Fetch both sniper and backup data
        cursor.execute(
            "SELECT sniper, antisniper_backup FROM guilds WHERE id = %s",
            (guild_id,)
        )
        result = cursor.fetchone()
        
        if not result:
            return text("antisnipe_notfound_error", lang)
        
        sniper_data = json.loads(result[0]) if result[0] else {}
        antisniper_data = json.loads(result[1]) if result[1] else {}
        channel_data = sniper_data.get(channel_id_str, [])
        
        if not channel_data:
            return text("antisnipe_notfound_error", lang)
        
        # Find and remove the most recent message from the user
        backup_data = None
        for i, message_data in enumerate(reversed(channel_data)):
            if message_data["author_id"] == user_id_str:
                backup_data = message_data
                channel_data.pop(len(channel_data) - 1 - i)
                break
        
        if not backup_data:
            return text("antisnipe_author_notfound_error", lang)
        
        # Update antisniper data with backup
        if channel_id_str not in antisniper_data:
            antisniper_data[channel_id_str] = []
        
        backup_data["date_antisniped"] = datetime.now().isoformat()
        antisniper_data[channel_id_str].append(backup_data)
        
        # Keep only last 30 messages
        if len(antisniper_data[channel_id_str]) > 30:
            antisniper_data[channel_id_str] = antisniper_data[channel_id_str][-30:]
        
        # Update with modified sniper data too
        sniper_data[channel_id_str] = channel_data
        cursor.execute(
            "UPDATE guilds SET sniper = %s, antisniper_backup = %s WHERE id = %s",
            (json.dumps(sniper_data), json.dumps(antisniper_data), guild_id)
        )
        connection.commit()
        return text("antisnipe_success", lang)
        
    except Exception as e:
        log.exception(e, "Error from _antisnipe")
        return text("antisnipe_unknown_error", lang)
    finally:
        connection.close()


async def antisnipe_text(lang: str, message: nextcord.Message):
    await message.reply(
        await _antisnipe(lang, message.author.id, message.guild.id, message.channel.id),
        mention_author=False
    )

async def antisnipe_text_slash(lang: str, interaction: nextcord.Interaction):
    await interaction.response.send_message(
        await _antisnipe(lang, interaction.user.id, interaction.guild.id, interaction.channel.id),
        ephemeral=True  # TODO: make this configurable?
    )


info = {
    "antisnipe": {
        "category": "utilities",
        "aliases": ["antisniper"],
        "hidden_aliases": ["antilog"],
        "available": ["slash_command", "text_command"],
        "dm_available": False,
        "visibility": "everyone",
        "user_permissions": [],
        "name": "antisnipe_name",
        "desc": "antisnipe_desc",
        "args": []
    }
}

cmd = CmdLocale(list(info.keys())[0], get_commands_locales(info))

class AntiSnipeCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @check_ban()
    @checks.guild_only()
    @slash_command(
        name=cmd.name,
        description=cmd.description,
        name_localizations=cmd.name_localizations,
        description_localizations=cmd.description_localizations
    )
    async def antisnipe_command(self, interaction: nextcord.Interaction):
        await antisnipe_text_slash(get_lang(interaction), interaction)


def setup(bot: commands.Bot):
    bot.add_cog(AntiSnipeCog(bot))

# Text command handler wrapper that adapts to message handler signature
@checks.guild_only()
async def _message_handler(bot, message: nextcord.Message, lang: str, guild_prefix: str):
    await antisnipe_text(lang, message)
