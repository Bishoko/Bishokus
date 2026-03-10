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
import json
import re
from utils.sql import get_db_connection


async def _get_channels(bot, guild_id: int) -> list[tuple[str, int]]:
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT confess_channels FROM guilds WHERE id = %s', (guild_id,))
    result = cursor.fetchone()

    channels = []
    if result and result[0]:
        try:
            channels_data = json.loads(result[0]) if isinstance(result[0], str) else result[0]
            channels = {}
            for channel_id in channels_data:
                channel = bot.get_channel(channel_id)
                if channel:
                    channels[f"#{channel.name} - ({channel.category})"] = str(channel_id)
                else:
                    channels[f"Unknown Channel ({channel_id})"] = str(channel_id)
        except (json.JSONDecodeError, TypeError):
            pass

    cursor.close()
    conn.close()
    return channels


async def _remove_confess_channel_from_db(guild_id: int, channel_id: int, lang: str):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Check if the guild already has confess channels
        cursor.execute('SELECT confess_channels FROM guilds WHERE id = %s', (guild_id,))
        result = cursor.fetchone()

        # Parse existing channels
        if result and result[0]:
            try:
                # Try to parse as JSON array
                channels = json.loads(result[0]) if isinstance(result[0], str) else result[0]
                if not isinstance(channels, list):
                    # Convert single value to list for backward compatibility
                    channels = [channels] if channels else []
            except (json.JSONDecodeError, TypeError):
                # If it's a single integer or invalid JSON, convert to list
                channels = [result[0]] if result[0] else []
        else:
            channels = []

        # Check if channel exists in the list
        if channel_id not in channels:
            cursor.close()
            conn.close()
            return text('settings_confess_removechannel_not_found', lang).replace('%channel%', f"<#{channel_id}>")

        # Remove the channel
        channels.remove(channel_id)
        
        # Store back as JSON
        channels_json = json.dumps(channels)
        cursor.execute('UPDATE guilds SET confess_channels = %s WHERE id = %s', (channels_json, guild_id))

        conn.commit()
        cursor.close()
        conn.close()
        return text('settings_confess_removechannel_success', lang).replace('%channel%', f"<#{channel_id}>")
        
    except Exception as e:
        log.exception(e, "Error removing confess channel from database")
        conn.rollback()
        cursor.close()
        conn.close()
        return text('settings_confess_removechannel_error', lang)


async def remove_confess_channel(lang: str, message: nextcord.Message):
    match = re.search(r'\d{17,19}', message.content)
    if match:
        channel_id = int(match.group())
        result = await _remove_confess_channel_from_db(message.guild.id, channel_id, lang)
        await message.reply(result, mention_author=False)
        return
    
    await message.reply(text('settings_confess_removechannel_notfound_error', lang), mention_author=False)
    return

async def remove_confess_channel_slash(lang: str, interaction: nextcord.Interaction, channel_id: int):
    result = await _remove_confess_channel_from_db(interaction.guild.id, channel_id, lang)
    await interaction.response.send_message(result, ephemeral=True)
    return


info = {
    "remove_confess_channel": {
        "category": "settings confess",
        "parent": "settings confess",
        "aliases": ["removeconfesschannel", "removeconfessionchannel", "remove_confession_channel", "removeconfess", "removeconfession",
                    "delconfesschannel", "delconfessionchannel", "del_confession_channel", "delconfess", "delconfession",
                    "deleteconfesschannel", "deleteconfessionchannel", "delete_confession_channel"],
        "aliases_sub_only": ["remove", "rem", "removechannel", "remove_channel",
                             "del", "delchannel", "del_channel",
                             "delete", "deletechannel", "delete_channel"],
        "hidden_aliases": [],
        "available": ["slash_command", "text_command"],
        "dm_available": False,
        "visibility": "everyone",
        "user_permissions": ["manage_guild"],
        "name": "settings_confess_removechannel_name",
        "desc": "settings_confess_removechannel_desc",
        "args": [
            {
                "name": "settings_confess_removechannel_arg_name",
                "desc": "settings_confess_removechannel_arg_desc",
                "required": True,
                "autocomplete": True
            }
        ]
    },
}

cmd = CmdLocale(list(info.keys())[0], get_commands_locales(info))

parent = gv.get('bot').get_cog("SettingsConfessCog").settings_confess
class RemoveConfessChannelCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    async def channel_autocomplete(self, interaction: nextcord.Interaction, current: str):
        """Provide autocomplete suggestions based on user's language"""
        return await _get_channels(self.bot, interaction.guild.id) if interaction.guild else []
    
    @check_ban()
    @guild_only()
    @parent.subcommand(
        name=cmd.name,
        description=cmd.description,
        name_localizations=cmd.name_localizations,
        description_localizations=cmd.description_localizations,
    )
    async def remove_confess_channel_command(self, interaction: nextcord.Interaction,
        channel: str = get_slash_option(cmd.arg(0))
    ):
        await remove_confess_channel_slash(get_lang(interaction), interaction, int(channel))
    
    @remove_confess_channel_command.on_autocomplete("channel")
    async def on_channel_autocomplete(self, interaction: nextcord.Interaction, channel: str):
        await interaction.response.send_autocomplete(await self.channel_autocomplete(interaction, channel))


def setup(bot: commands.Bot):
    bot.add_cog(RemoveConfessChannelCog(bot))

# Text command handler wrapper that adapts to message handler signature
async def _message_handler(bot, message: nextcord.Message, lang_str: str, prefix_str: str):
    await remove_confess_channel(lang_str, message)
