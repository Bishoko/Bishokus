import nextcord

from utils import config
from utils.logger import log
from utils.settings.bot_ban import is_banned
from handlers.on_guild_join import log_guild_count


async def handle_guild_remove(bot, guild: nextcord.Guild):
    if is_banned(guild.id, is_guild=True):
        return
    
    log.info(f"Left guild: {guild.name} (ID: {guild.id})")
    
    log_guild_count(bot)
    
    try:
        notification_channel = bot.get_channel(config["new-guild-notification-channel"])
        if notification_channel:
            await notification_channel.send(
                f"**__Server left:__** {guild.name}\n"
                f"**__Owner:__** ||`{guild.owner}` (`{guild.owner_id}`)  -  <@{guild.owner_id}>||\n"
                f"**__Members:__** {guild.member_count}"
            )
    except Exception as e:
        log.exception(e, "Error sending guild removal notification.")
