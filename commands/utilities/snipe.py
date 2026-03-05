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

import json
from datetime import datetime
import utils.global_variables as gv
from utils.sql import get_db_connection


bot = gv.get("bot")
@bot.event
async def on_message_delete(message: nextcord.Message):
    # Skip messages without content or from DMs
    if not message.system_content or not message.guild:
        return
    
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        
        # Fetch current data
        cursor.execute(
            "SELECT sniper FROM guilds WHERE id = %s",
            (message.guild.id,)
        )
        result = cursor.fetchone()
        
        sniper_data = json.loads(result[0]) if result and result[0] else {}
        channel_id = str(message.channel.id)
        if not sniper_data.get(channel_id):
            sniper_data[channel_id] = []
        
        sniper_data[channel_id].append({
            "message": message.system_content,
            "author": message.author.display_name,
            "date_sent": message.created_at.isoformat(),
            "date_removed": datetime.now().isoformat()
        })
        
        # Keep only last 10 messages
        if len(sniper_data[channel_id]) > 10:
            sniper_data[channel_id].pop(0)
        
        # Update database with new data
        cursor.execute(
            "UPDATE guilds SET sniper = %s WHERE id = %s",
            (json.dumps(sniper_data), message.guild.id)
        )
        connection.commit()
        
    finally:
        cursor.close()
        connection.close()


async def _snipe_embed(lang: str, guild_id: int, channel_id: int, maximum: int=5):
    maximum = int(maximum) if maximum else 5
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT sniper FROM guilds WHERE id = %s", (guild_id,))
    result = cursor.fetchone()
    cursor.close()
    connection.close()

    if result and result[0]:
        content = json.loads(result[0]).get(str(channel_id), {})
        if not content:
            # Error if nothing found in db
            embed = nextcord.Embed(
                title="Sniper",
                description=text("snipe_empty_error", lang),
                color=config.get("embed-color")
            )
            return embed
    
        description = ""
        for i, item in enumerate(content[-maximum:]):
            date_removed = datetime.fromisoformat(item['date_removed']).strftime(text("snipe_time_format", lang))
            description += f"`[{date_removed}]` **{item['author']} :** {item['message']}\n"
            
        embed = nextcord.Embed(
            title="Sniper",
            description=description,
            color=config.get("embed-color")
        )
        return embed
    else:
        embed = nextcord.Embed(
            title="Sniper",
            description=text("snipe_unknown_error", lang),
            color=config.get("embed-color")
        )
        return embed


async def snipe_text(lang: str, message: nextcord.Message):
    maximum = int(message.content) if message.content.isdigit() else None
    snipeembed = await _snipe_embed(lang, message.guild.id, message.channel.id, maximum=maximum)
    if snipeembed:
        await message.reply(embed=snipeembed, mention_author=False)

async def snipe_text_slash(lang: str, interaction: nextcord.Interaction, max_count: str):
    snipeembed = await _snipe_embed(lang, interaction.guild.id, interaction.channel.id, maximum=max_count)
    if snipeembed:
        await interaction.response.send_message(embed=snipeembed)


info = {
    "snipe": {
        "category": "utilities",
        "aliases": ["sniper"],
        "hidden_aliases": ["log", "lastmsg", "last_message", "last", "seelast",],
        "available": ["slash_command", "text_command"],
        "visibility": "everyone",
        "user_permissions": [],
        "name": "snipe_name",
        "desc": "snipe_desc",
        "args": [
            {
                "name": "snipe_arg_name",
                "desc": "snipe_arg_desc",
                "min_value": 1,
                "max_value": 5,
                "required": False,
            }
        ]
    }
}

cmd = CmdLocale(list(info.keys())[0], get_commands_locales(info))

class SnipeCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @check_ban()
    @application_checks.has_permissions(**{perm: True for perm in cmd.user_permissions})
    @slash_command(
        name=cmd.name,
        description=cmd.description,
        name_localizations=cmd.name_localizations,
        description_localizations=cmd.description_localizations
    )
    async def snipe_command(self, interaction: nextcord.Interaction,
        max_count: int = get_slash_option(cmd.arg(0))
    ):
        await snipe_text_slash(get_lang(interaction), interaction, max_count)


def setup(bot: commands.Bot):
    bot.add_cog(SnipeCog(bot))

# Text command handler wrapper that adapts to message handler signature
async def _message_handler(bot, message: nextcord.Message, lang: str, prefix: str):
    await snipe_text(lang, message)
