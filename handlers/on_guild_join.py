import nextcord
from unidecode import unidecode

from utils.logger import log
from utils.sql import get_db_connection
from utils.settings.bot_ban import get_ban_type
from utils.config import config
from utils.languages import text
from utils.settings.lang import set_guild as set_guild_language
from utils.settings.prefix import get as get_prefix


class LanguageSwitchView(nextcord.ui.View):
    def __init__(self, guild: nextcord.Guild, current_lang: str = 'fr'):
        super().__init__(timeout=None)
        target_lang = 'en' if current_lang.lower().startswith('fr') else 'fr'
        self.add_item(LanguageSwitchButton(guild, target_lang))


class LanguageSwitchButton(nextcord.ui.Button):
    LANG_CODES = {'en': 'en_US', 'fr': 'fr'}

    def __init__(self, guild: nextcord.Guild, target_lang: str):
        self.guild = guild
        self.target_lang = target_lang
        super().__init__(
            label=text('on_guild_join_switch_lang_button', target_lang),
            style=nextcord.ButtonStyle.success,
            custom_id=f"switch_lang_{target_lang}",
        )

    async def callback(self, interaction: nextcord.Interaction):
        await interaction.response.defer()

        try:
            set_guild_language(self.guild.id, self.LANG_CODES[self.target_lang])
        except Exception as e:
            log.exception(e, f"Error setting guild language to {self.target_lang}")

        embed = _build_welcome_embed(self.guild, self.target_lang)
        view = LanguageSwitchView(self.guild, self.target_lang)
        await interaction.edit_original_message(embed=embed, view=view)


def _build_welcome_embed(guild: nextcord.Guild, lang: str) -> nextcord.Embed:
    embed = nextcord.Embed(
        title=f"<:Bishokus:946583577372536864> {text('on_guild_join_embed_title', lang).replace('%guild_name%', guild.name)}",
        description=text('on_guild_join_embed_desc', lang).replace('%prefix%', get_prefix(guild.id)),
        color=config.get("embed-color")
    )
    field_lines = [
        text('on_guild_join_embed_field_value_l1', lang),
        text('on_guild_join_embed_field_value_l2', lang),
        text('on_guild_join_embed_field_value_l3', lang),
        text('on_guild_join_embed_field_value_l4', lang),
    ]
    field_value = '\n'.join(line for line in field_lines if line) + '\n\n' + f"[{text('on_guild_join_embed_field_value_link_text', lang)}]({config.get('invite-url')})"
    embed.add_field(
        name=text('on_guild_join_embed_field_title', lang),
        value=field_value,
        inline=False
    )
    embed.set_footer(text=text('on_guild_join_embed_footer', lang))
    embed.set_thumbnail(url=config.get("bot-avatar-url"))
    return embed


def log_guild_count(bot: nextcord.Client):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO guild_count (`time`, count) VALUES (CURRENT_TIMESTAMP, %s)', (len(bot.guilds),))
    conn.commit()
    cursor.close()
    conn.close()

def _get_welcome_channel(guild: nextcord.Guild):
    channel_keywords = ["general", "chat", "staff", "moderation", "admins", "bienvenue"]
    
    # Try to find a channel with pertinent keywords
    for channel in guild.text_channels:
        channel_name = unidecode(channel.name.strip().lower(), errors="preserve")  # Remove accents and convert to lowercase
        channel_name = ''.join(ch for ch in channel_name if ch.isalnum() or ch == " ")  # Remove symbols
        if channel_name in channel_keywords:
            return channel
    
    # If not found, return the first text channel where the bot has permission to send messages
    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).send_messages:
            return channel
    
    # Fallback to owner DMs if no suitable channel is found
    return guild.owner.dm_channel


async def handle_guild_join(bot, guild: nextcord.Guild):
    if get_ban_type(guild.id, is_guild=True) == 'instant_leave':
        await guild.leave()
        log.info(f"Left banned guild: {guild.name} (ID: {guild.id})")
        return
    
    log.info(f"Joined guild: {guild.name} (ID: {guild.id})")
    
    log_guild_count(bot)
    
    welcome_channel = _get_welcome_channel(guild)
    
    try:
        notification_channel = bot.get_channel(config["new-guild-notification-channel"])
        if notification_channel:
            await notification_channel.send(
                f"**__New server:__** {guild.name}\n"
                f"**__Message sent in:__** {welcome_channel.name if welcome_channel else 'N/A'}\n"
                f"**__Owner:__** ||`{guild.owner}` (`{guild.owner_id}`)  -  <@{guild.owner_id}>||\n"
                f"**__Members:__** {guild.member_count}"
            )
    except Exception as e:
        log.exception(e, "Error sending new guild notification.")
    
    # Create embed with French as default language
    embed = _build_welcome_embed(guild, 'fr')
    
    # Add language switch view (default French, so only show English button)
    view = LanguageSwitchView(guild, 'fr')
    
    if welcome_channel:
        await welcome_channel.send(embed=embed, view=view)
