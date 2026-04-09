import nextcord
from unidecode import unidecode

from utils.logger import log
from utils.sql import get_db_connection
from utils.settings.bot_ban import get_ban_type
from utils.config import config


def _log_guild_count(bot: nextcord.Client):
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
    
    _log_guild_count(bot)
    
    try:
        notification_channel = bot.get_channel(config["new-guild-notification-channel"])
        if notification_channel:
            await notification_channel.send(
                f"**__New server:__** {guild.name}\n" \
                f"**__Message sent in:__** {welcome_channel.name}\n" \
                f"**__Owner:__** ||`{guild.owner}` (`{guild.owner_id}`)  -  <@{guild.owner_id}>||\n" \
                f"**__Members:__** {guild.member_count}"
            )
    except Exception as e:
        log.exception(e, "Error sending new guild notification.")
    
    embed = nextcord.Embed(
        title=f"<:Bishokus:946583577372536864> Merci beaucoup d'avoir ajouté Bishokus sur __{guild.name}__!",
        description="Mon préfixe est pour l'instant `!` ou `@Bishokus 🧎#1363`.",
        color=config.get("embed-color")
    )
    embed.add_field(
        name="A savoir",
        value="- **/help** pour voir les commandes\n" \
              "- **/paramètres langue** pour changer la langue\n" \
              "- **/paramètres prefixe** pour changer le préfixe\n" \
              "- **!jdm** pour activer les jeux de mots\n" \
              "\n" \
              "[Ajouter Bishokus](https://discord.com/api/oauth2/authorize?client_id=854081099638112256&permissions=277582703681&scope=bot%20applications.commands)",
        inline=False
    )
    embed.set_footer(
        text=f"Utilisez /support pour plus d'aide :)"
    )
    embed.set_thumbnail(
        url=config.get("bot-avatar-url")
    )
    
    welcome_channel = _get_welcome_channel(guild)
    if welcome_channel:
        await welcome_channel.send(embed=embed)
