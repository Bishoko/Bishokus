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

import random

# Ben settings
WEBHOOK_AVATARS = {
    "yes": 'https://raw.githubusercontent.com/Bishoko/Bishokus/refs/heads/main/medias/yes.gif',
    "no": 'https://raw.githubusercontent.com/Bishoko/Bishokus/refs/heads/main/medias/no.gif',
    "hohoho": 'https://raw.githubusercontent.com/Bishoko/Bishokus/refs/heads/main/medias/hohoho.gif',
    "ugh": 'https://raw.githubusercontent.com/Bishoko/Bishokus/refs/heads/main/medias/ugh.gif',
    "bye": 'https://raw.githubusercontent.com/Bishoko/Bishokus/refs/heads/main/medias/ben.gif',
    "default": 'https://raw.githubusercontent.com/Bishoko/Bishokus/refs/heads/main/medias/ben.gif',
}
HANG_UP_GIF_URL = 'https://raw.githubusercontent.com/Bishoko/Bishokus/refs/heads/main/medias/hang_up.gif'
MAXIMUM_WEBHOOKS_PER_GUILD = 3


async def _cleanup_excess_webhooks(bot: commands.Bot, guild: nextcord.Guild, current_webhook: nextcord.Webhook = None):
    """Clean up excess webhooks, keeping only the most recent ones."""
    webhooks = await guild.webhooks()
    bot_webhooks = [wh for wh in webhooks if wh.user and wh.user.id == bot.user.id]
    
    # If we have too many webhooks, delete the oldest ones
    if len(bot_webhooks) > MAXIMUM_WEBHOOKS_PER_GUILD:
        # Sort by creation time, oldest first
        bot_webhooks.sort(key=lambda wh: wh.id)
        excess_count = len(bot_webhooks) - MAXIMUM_WEBHOOKS_PER_GUILD
        
        for webhook in bot_webhooks[:excess_count]:
            if current_webhook is None or webhook.id != current_webhook.id:
                try:
                    await webhook.delete()
                except Exception as e:
                    log.warning(f"Failed to delete excess webhook {webhook.id} in guild {guild.id}: {e}")

async def _get_or_create_webhook(bot: commands.Bot, message: nextcord.Message) -> nextcord.Webhook:
    """Get or create a webhook for the Ben command in the current channel."""
    webhooks = await message.guild.webhooks()
    finalwebhook = None
    
    # Look for existing Ben webhook in this channel
    for webhook in webhooks:
        if webhook.user and webhook.user.id == bot.user.id:
            if webhook.channel_id == message.channel.id:
                finalwebhook = webhook
                break
    
    # Create a new webhook if none exists
    if not finalwebhook:
        finalwebhook = await message.channel.create_webhook(name='Bishokus Webhook (ben)')
    
    # Clean up excess webhooks
    await _cleanup_excess_webhooks(bot, message.guild, finalwebhook)
    
    return finalwebhook


def _get_ben_response(lang: str, has_message: bool) -> tuple[str, str]:
    """
    Generate Ben's response and determine which avatar to use.
    Returns (response_text, avatar_key)
    """
    if has_message:
        # Random chance of sending the "bye" response
        if random.randint(1, 20) == 1:
            return HANG_UP_GIF_URL, "default"
        
        # Otherwise, random response
        response_type = random.choice(["yes", "no", "hohoho", "ugh"])
        return text(f'ben_response_{response_type}', lang), response_type
    else:
        # Default response when no message is provided
        return text('ben_response_default', lang), "default"


async def _send_ben_response(webhook: nextcord.Webhook, lang: str, has_message: bool):
    """Send Ben's response via webhook."""
    response_text, avatar_key = _get_ben_response(lang, has_message)
    avatar_url = WEBHOOK_AVATARS.get(avatar_key, WEBHOOK_AVATARS["default"])
    
    await webhook.send(
        response_text,
        username="Ben",
        avatar_url=avatar_url
    )


async def ben(bot: commands.Bot, lang: str, message: nextcord.Message):
    """Text command handler for Ben."""
    try:
        webhook = await _get_or_create_webhook(bot, message)
        await _send_ben_response(
            webhook, lang, has_message=bool(message.content)
        )
    except nextcord.errors.Forbidden:
        await message.channel.send(text('ben_webhook_permission_error', lang))

async def ben_slash(bot: commands.Bot, lang: str, interaction: nextcord.Interaction, message_content: str):
    """Slash command handler for Ben."""
    try:
        # For slash commands, we need to get the guild from interaction
        webhooks = await interaction.guild.webhooks()
        finalwebhook = None
        
        for webhook in webhooks:
            if webhook.user and webhook.user.id == bot.user.id:
                if webhook.channel_id == interaction.channel_id:
                    finalwebhook = webhook
                    break
                else:
                    try:
                        await webhook.delete()
                    except Exception as e:
                        log.warning(f"Failed to delete excess webhook {webhook.id} in guild {interaction.guild.id}: {e}")
        
        if not finalwebhook:
            finalwebhook = await interaction.channel.create_webhook(name='Bishokus Webhook (ben)')
        
        has_message = bool(message_content)
        await _send_ben_response(finalwebhook, lang, has_message)
        await interaction.response.send_message(
            text('ben_success_1', lang) if not has_message else text('ben_success_2', lang),
            ephemeral=True
        )
    except nextcord.errors.Forbidden:
        await interaction.response.send_message(text('ben_webhook_permission_error', lang))


info = {
    "ben": {
        "category": "fun",
        "aliases": [],
        "hidden_aliases": ["talking_ben", "talkingben", "talking-ben"],
        "available": ["text_command", "slash_command"],
        "dm_available": False,
        "visibility": "everyone",
        "user_permissions": [],
        "name": "ben_name",
        "desc": "ben_desc",
        "args": [
            {
                "name": "ben_name",
                "desc": "ben_desc",
                "required": False
            }
        ]
    },
}

cmd = CmdLocale(list(info.keys())[0], get_commands_locales(info))

class benCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @check_ban()
    @checks.guild_only()
    @checks.bot_permissions(manage_webhooks=True)
    @slash_command(
        name=cmd.name,
        description=cmd.description,
        name_localizations=cmd.name_localizations,
        description_localizations=cmd.description_localizations
    )
    async def ben_command(self, interaction: nextcord.Interaction,
        message_content: str = get_slash_option(cmd.arg(0))
    ):
        await ben_slash(self.bot, get_lang(interaction), interaction, message_content)


def setup(bot: commands.Bot):
    bot.add_cog(benCog(bot))

# Text command handler wrapper that adapts to message handler signature
@checks.guild_only()
@checks.bot_permissions(manage_webhooks=True)
async def _message_handler(bot, message: nextcord.Message, lang: str, guild_prefix: str):
    await ben(bot, lang, message)
