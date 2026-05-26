import nextcord
from nextcord.ext import commands, application_checks
from nextcord.application_command import slash_command, message_command
from utils.logger import log
from utils.get_commands_locales import get_commands_locales
from utils.locale_helpers import CmdLocale, get_slash_option
from utils import config
from utils.settings.bot_ban import check_ban
from utils.languages import text
from utils.settings import prefix
from utils.settings.lang import get_lang

import json
from datetime import datetime
from utils.sql import get_db_connection
from utils.get_urls import get_urls

ALLOWED_MEDIA_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.avif']
# Track confess cooldowns in memory: {(user_id, channel_id): expiration_time}
CONFESS_COOLDOWNS = {}


def _extract_media_urls(attachments: list[nextcord.Attachment], message_content: str) -> list:
    """Extract valid media URLs from attachments"""
    # TODO: Add support for videos (embed.video)
    media_urls = []
    for attachment in attachments:
        extension = attachment.filename.lower().rsplit('.', 1)[-1] if '.' in attachment.filename else ''
        if f'.{extension}' in ALLOWED_MEDIA_EXTENSIONS:
            media_urls.append(attachment.url)
    
    # Also extract media urls in the message.content
    urls = get_urls(message_content)
    for url in urls:
        if any(url.lower().rsplit('?', 1)[0].endswith(ext) for ext in ALLOWED_MEDIA_EXTENSIONS):
            media_urls.append(url)
    
    return media_urls


def _get_user_confess_channels(bot, user_id: int) -> list:
    """Get all confession channels where the user can confess"""
    confess_channels = []
    
    for guild in bot.guilds:
        # Check if user is member of guild
        member = guild.get_member(user_id)
        if member is None:
            continue
        
        # Query database for confession channels
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            "SELECT confess_channels FROM guilds WHERE id = %s",
            (guild.id,)
        )
        result = cursor.fetchone()
        cursor.close()
        connection.close()
        
        if result is None:
            continue
        
        try:
            channels_data = json.loads(result[0])
            for channel_id in channels_data:
                if channel_id and channel_id != "None":
                    channel = bot.get_channel(int(channel_id))
                    if channel:
                        confess_channels.append({
                            'guild': guild,
                            'channel': channel,
                            'guild_id': guild.id,
                            'channel_id': int(channel_id)
                        })
        except (json.JSONDecodeError, ValueError):
            continue
    
    return confess_channels


def _is_user_banned(guild_id: int, user_id: int) -> bool:
    """Check if user is banned from confessing in this guild"""
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute(
        "SELECT confess_banned FROM guilds WHERE id = %s",
        (guild_id,)
    )
    result = cursor.fetchone()
    cursor.close()
    connection.close()
    
    if result is None:
        return False
    
    try:
        banned_data = json.loads(result[0])
        return str(user_id) in banned_data
    except (json.JSONDecodeError, ValueError):
        return False


async def _log_confession(user: nextcord.User, guild_id: int, channel_id: int, guild_name: str, channel_name: str, message: str, media_urls: list):
    """Log confession to database"""
    connection = get_db_connection()
    cursor = connection.cursor()
    
    # Combine message and media URLs
    full_message = message
    if media_urls:
        full_message += " " + " ".join(media_urls)
    
    try:
        cursor.execute(
            """INSERT INTO confess (guild_id, channel_id, user_id, guild_name, channel_name, user_name, raw_message)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (guild_id, channel_id, user.id, guild_name, channel_name, str(user), full_message)
        )
        connection.commit()
    except Exception as e:
        log.exception(e, "Error logging confession")
    finally:
        cursor.close()
        connection.close()


async def _send_confession(bot, channel_info: dict, user: nextcord.User, message: str, media_urls: list, lang: str):
    """Send confession to target channel and return success status"""
    try:
        embed = nextcord.Embed(
            title="",
            description=message,
            color=config.get('embed-color'),
            timestamp=datetime.now()
        )
        embed.set_author(
            name=text('confess_anonymous_author', lang),
            icon_url=channel_info['guild'].icon.url if channel_info['guild'].icon else None
        )
        
        if media_urls:
            embed.set_image(url=media_urls[0])
            # TODO: check if adding multiple media is possible in nextcord embeds and if so add them here
        
        embed.set_footer(text=f"{text('confess_footer', lang)}")
        
        await channel_info['channel'].send(embed=embed)
        
        # Log to database
        await _log_confession(
            user,
            channel_info['guild_id'],
            channel_info['channel_id'],
            channel_info['guild'].name,
            channel_info['channel'].name,
            message,
            media_urls
        )
        
        return True
    except Exception as e:
        log.exception(e, "Error sending confession")
        return False


async def _confess(bot, user: nextcord.User, message_content: str, attachments: list[nextcord.Attachment], lang: str, guild_id: int = 0, channel_id: int = 0) -> tuple:
    """Core confess logic used by both slash and text commands"""
    
    # Validate message not empty
    media_urls = _extract_media_urls(attachments, message_content)
    message_content = message_content.strip()
    # Remove media URLs from message content to avoid confusion
    for media_url in media_urls:
        message_content = message_content.replace(media_url, '').strip()
    
    if not message_content and not media_urls:
        embed = nextcord.Embed(
            title=text('confess_title', lang),
            description=text('confess_empty_error', lang),
            color=config.get('embed-color')
        )
        return embed, None
    
    # Get confession channels
    confess_channels = _get_user_confess_channels(bot, user.id)
    
    if not confess_channels:
        embed = nextcord.Embed(
            title=text('confess_title', lang),
            description=text('confess_no_channels_error', lang),
            color=config.get('embed-color')
        )
        return embed, None
    
    # Create selection view
    class ConfessView(nextcord.ui.View):
        def __init__(self, guild_id: int = 0, channel_id: int = 0):
            super().__init__(timeout=None)
            self.value = None
            self.guild_id = guild_id
            self.channel_id = channel_id
        
        async def create_buttons(self):
            def _sort_channels(channels):
                """Sort channels to prioritize those where the user is typing in"""
                sorted_guilds = []
                sorted_channels = []
                for ch in channels:
                    if ch['guild_id'] == self.guild_id:
                        sorted_guilds.insert(0, ch)  # Put current guild channels first
                    else:
                        sorted_guilds.append(ch)
                for ch in sorted_guilds:
                    if ch['channel_id'] == self.channel_id:
                        ch['is_actual_channel'] = True
                        sorted_channels.insert(0, ch)  # Put current channel first
                    else:
                        ch['is_actual_channel'] = False
                        sorted_channels.append(ch)
                return sorted_channels
                
            confess_channels_sorted = _sort_channels(confess_channels)
            
            for i, channel_info in enumerate(confess_channels_sorted, 1):
                is_banned = _is_user_banned(channel_info['guild_id'], user.id)
                guild_name = channel_info['guild'].name
                channel_name = channel_info['channel'].name
                button_label = f"{guild_name} » #{channel_name}"
                
                # Nextcord has a 80 character limit for button labels
                if len(button_label) > 80:
                    button_label = button_label[:77] + "..."
                
                async def button_callback(interaction: nextcord.Interaction, ch_info=channel_info, idx=i):
                    await interaction.response.defer()
                    
                    # Check ban status
                    if _is_user_banned(ch_info['guild_id'], user.id):
                        embed = nextcord.Embed(
                            title="",
                            description=text('confess_user_banned_error', lang),
                            color=config.get('embed-color')
                        )
                        embed.set_author(
                            name=text('confess_title', lang),
                            icon_url=ch_info['guild'].icon.url if ch_info['guild'].icon else None
                        )
                        try:
                            await interaction.edit_original_message(embed=embed, view=None)
                        except Exception as e:
                            log.warning(f"Failed to edit original message for interaction {interaction.id} in guild {interaction.guild.id}: {e}")
                        return
                    
                    # Check cooldown
                    cooldown_key = (user.id, ch_info['channel_id'])
                    
                    connection = get_db_connection()
                    cursor = connection.cursor()
                    cursor.execute(
                        "SELECT confess_cooldown FROM guilds WHERE id = %s",
                        (ch_info['guild_id'],)
                    )
                    result = cursor.fetchone()
                    cursor.close()
                    connection.close()
                    
                    cooldown = int(result[0]) if result else 0
                    current_time = datetime.now().timestamp()
                    
                    if cooldown_key in CONFESS_COOLDOWNS and CONFESS_COOLDOWNS[cooldown_key] > current_time:
                        embed = nextcord.Embed(
                            title="",
                            description=text('confess_cooldown_error', lang).replace('%seconds%', str(cooldown)),
                            color=config.get('embed-color')
                        )
                        embed.set_author(
                            name=f"{text('confess_title', lang)} » {ch_info['guild'].name}",
                            icon_url=ch_info['guild'].icon.url if ch_info['guild'].icon else None
                        )
                        try:
                            await interaction.edit_original_message(embed=embed, view=None)
                        except Exception as e:
                            log.warning(f"Failed to edit original message for interaction {interaction.id} in guild {interaction.guild.id}: {e}")
                        return
                    
                    # Send confession
                    success = await _send_confession(bot, ch_info, user, message_content, media_urls, lang)
                    
                    if success:
                        embed = nextcord.Embed(
                            title="",
                            description=text('confess_sent_success', lang).replace('%guild%', ch_info['guild'].name),
                            color=config.get('embed-color'),
                            timestamp=datetime.now()
                        )
                        embed.set_author(
                            name=f"{("📝 " if not ch_info['guild'].icon else "")}{text('confess_title', lang)} » {ch_info['guild'].name}",
                            icon_url=ch_info['guild'].icon.url if ch_info['guild'].icon else None
                        )
                        embed.add_field(name=text('confess_channel_field', lang),
                            value=ch_info['channel'].mention,
                            inline=True
                        )
                        
                        # Set cooldown in memory
                        if cooldown > 0:
                            CONFESS_COOLDOWNS[cooldown_key] = current_time + cooldown
                    else:
                        embed = nextcord.Embed(
                            title="",
                            description=text('confess_send_error', lang),
                            color=config.get('embed-color')
                        )
                    
                    try:
                        await interaction.edit_original_message(embed=embed, view=None)
                    except Exception as e:
                        log.warning(f"Failed to edit original message for interaction {interaction.id} in guild {interaction.guild.id}: {e}")
                    
                    self.value = True
                    self.stop()
                
                button = nextcord.ui.Button(
                    label=button_label,
                    style=nextcord.ButtonStyle.grey if is_banned else nextcord.ButtonStyle.green if not channel_info.get('is_actual_channel', False) else nextcord.ButtonStyle.blurple,
                    disabled=is_banned
                )
                button.callback = button_callback
                self.add_item(button)
        
        @nextcord.ui.button(label=text('confess_cancel', lang), style=nextcord.ButtonStyle.danger)
        async def cancel_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
            await interaction.response.defer()
            
            embed = nextcord.Embed(
                title="",
                description="",
                color=config.get('embed-color')
            )
            user_obj = await bot.fetch_user(interaction.user.id)
            embed.set_author(
                name=text('confess_cancelled', lang),
                icon_url=user_obj.avatar.url if user_obj.avatar else None
            )
            
            try:
                await interaction.edit_original_message(embed=embed, view=None)
            except Exception as e:
                log.warning(f"Failed to edit original message for interaction {interaction.id} in guild {interaction.guild.id}: {e}")
            
            self.value = True
            self.stop()
    
    view = ConfessView(
        guild_id=guild_id,
        channel_id=channel_id,
    )
    await view.create_buttons()
    
    # Create main embed
    channel_list = "\n".join([f"> {ch['guild'].name} » #{ch['channel'].name}" for ch in confess_channels])
    embed = nextcord.Embed(
        title=text('confess_title', lang),
        description=f"{text('confess_available_channels', lang)}\n{channel_list}\n",
        color=config.get('embed-color')
    )
    embed.set_footer(text=text('confess_select_channel', lang))
    
    return embed, view


async def confess_text(lang: str, bot: commands.Bot, message: nextcord.Message):
    """Handle text command"""
    embed, view = await _confess(
        bot=bot,
        user=message.author,
        message_content=message.content,
        attachments=message.attachments,
        lang=lang,
        guild_id=message.guild.id if message.guild else 0,
        channel_id=message.channel.id if message.channel else 0,
    )
    
    await message.reply(
        embed=embed, mention_author=False,
        view=view if view else None
    )

async def confess_slash(lang: str, interaction: nextcord.Interaction, message: str = "", media: nextcord.Attachment = None, media_url: str = ""):
    """Handle slash command"""
    if not message and not media and not media_url:
        embed = nextcord.Embed(
            title=text('confess_title', lang),
            description=text('confess_empty_error', lang),
            color=config.get('embed-color')
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    embed, view = await _confess(
        bot=interaction.client,
        user=interaction.user,
        message_content=message if message else "" + media_url if media_url else "",
        attachments=[media] if media else [],
        lang=lang,
        guild_id=interaction.guild.id if interaction.guild else 0,
        channel_id=interaction.channel.id if interaction.channel else 0,
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True if interaction.guild else False,
        view=view if view else nextcord.utils.MISSING
    )


info = {
    "confess": {
        "category": "fun",
        "aliases": ["confession"],
        "hidden_aliases": ["confesser", "confes", "javoue"],
        "available": ["text_command", "slash_command"],
        "visibility": "everyone",
        "user_permissions": [],
        "name": "confess_name",
        "desc": "confess_desc",
        "args": [
            {
                "name": "confess_message_arg_name",
                "desc": "confess_message_arg_desc",
                "required": False
            },
            {
                "name": "confess_media_arg_name",
                "desc": "confess_media_arg_desc",
                "required": False
            },
            {
                "name": "confess_media_url_arg_name",
                "desc": "confess_media_url_arg_desc",
                "required": False
            },
        ]
    },
}

cmd = CmdLocale(list(info.keys())[0], get_commands_locales(info))

class confessCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @check_ban()
    @slash_command(
        name=cmd.name,
        description=cmd.description,
        name_localizations=cmd.name_localizations,
        description_localizations=cmd.description_localizations
    )
    async def confess_command(self, interaction: nextcord.Interaction,
        message: str = get_slash_option(cmd.arg(0)),
        media: nextcord.Attachment = get_slash_option(cmd.arg(1)),
        media_url: str = get_slash_option(cmd.arg(2)),
    ):
        await confess_slash(get_lang(interaction), interaction, message, media, media_url)


def setup(bot: commands.Bot):
    bot.add_cog(confessCog(bot))
        
async def _message_handler(bot, message: nextcord.Message, lang: str, guild_prefix: str):
    await confess_text(lang, bot, message)
