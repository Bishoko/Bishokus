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
import json
import re
from utils.sql import get_db_connection


async def _add_confess_channel_to_db(guild_id: int, channel_id: int, lang: str):
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

        # Check if channel already exists
        if channel_id in channels:
            cursor.close()
            conn.close()
            return text('settings_confess_addchannel_already_exists', lang).replace('%channel%', f"<#{channel_id}>")

        # Check if maximum of 5 channels is reached
        if len(channels) >= 5:
            cursor.close()
            conn.close()
            # TODO: before sending this error, check if some of the channels in the list don't exist anymore
            # or if the bot doesn't have access to them, and if so, remove them from the list and allow adding a new one
            return text('settings_confess_addchannel_maximum_error', lang)

        # Add new channel
        channels.append(channel_id)
        
        # Store back as JSON
        channels_json = json.dumps(channels)
        cursor.execute('UPDATE guilds SET confess_channels = %s WHERE id = %s', (channels_json, guild_id))

        conn.commit()
        cursor.close()
        conn.close()
        return text('settings_confess_addchannel_success', lang).replace('%channel%', f"<#{channel_id}>")
        
    except Exception as e:
        print(f"Error updating confess channel in database: {e}")
        conn.rollback()
        cursor.close()
        conn.close()
        return text('settings_confess_addchannel_error', lang)


async def add_confess_channel(lang: str, message: nextcord.Message):
    match = re.search(r'\d{17,19}', message.content)
    if match:
        channel_id = int(match.group())
        result = await _add_confess_channel_to_db(message.guild.id, channel_id, lang)
        await message.reply(result, mention_author=False)
        return
    
    await message.reply(text('settings_confess_addchannel_notfound_error', lang), mention_author=False)
    return

async def add_confess_channel_slash(lang: str, interaction: nextcord.Interaction, new_channel: nextcord.TextChannel):
    result = await _add_confess_channel_to_db(interaction.guild.id, new_channel.id, lang)
    await interaction.response.send_message(result, ephemeral=True)
    return


info = {
    "add_confess_channel": {
        "category": "settings confess",
        "parent": "settings confess",
        "aliases": ["addconfesschannel", "addconfessionchannel", "add_confession_channel", "addconfess", "addconfession",
                    "setconfesschannel", "setconfessionchannel", "set_confession_channel", "setconfess", "setconfession"],
        "aliases_sub_only": ["add", "addchannel", "add_channel",
                             "set", "setchannel", "set_channel"],
        "hidden_aliases": ["setserverlang", "setserverlanguage", "set_serverlang", "set_server_lang", "setguildlang", "set_guildlang", "set_guild_lang", "guild_lang", "guildlang"],
        "available": ["slash_command", "text_command"],
        "visibility": "everyone",
        "user_permissions": ["manage_guild"],
        "name": "settings_confess_addchannel_name",
        "desc": "settings_confess_addchannel_desc",
        "args": [
            {
                "name": "settings_confess_addchannel_arg_name",
                "desc": "settings_confess_addchannel_arg_desc"
            }
        ]
    },
}

cmd = CmdLocale(list(info.keys())[0], get_commands_locales(info))

parent = gv.get('bot').get_cog("SettingsConfessCog").settings_confess
class AddConfessChannelCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @check_ban()
    @application_checks.has_permissions(**{perm: True for perm in cmd.user_permissions})
    @parent.subcommand(
        name=cmd.name,
        description=cmd.description,
        name_localizations=cmd.name_localizations,
        description_localizations=cmd.description_localizations,
    )
    async def add_confess_channel_command(self, interaction: nextcord.Interaction,
        new_channel: nextcord.TextChannel = get_slash_option(cmd.arg(0))
    ):
        await add_confess_channel_slash(get_lang(interaction), interaction, new_channel)


def setup(bot: commands.Bot):
    bot.add_cog(AddConfessChannelCog(bot))

# Text command handler wrapper that adapts to message handler signature
async def _message_handler(bot, message: nextcord.Message, lang_str: str, prefix_str: str):
    await add_confess_channel(lang_str, message)
