import nextcord

from utils.settings import bot_ban


async def bot_ban_guild(interaction: nextcord.Interaction, guild_id: int, ban_type: str, reason: str):

    bot_ban.ban_guild(guild_id, ban_type, reason)

    await interaction.response.send_message("Guild has been banned successfully.")
    
    
async def bot_unban_guild(interaction: nextcord.Interaction, guild_id: int, confirmation: str):
    if confirmation.lower() != 'yes':
        await interaction.response.send_message("Unban operation cancelled.")
        return

    if not bot_ban.is_banned(guild_id, is_guild=True):
        await interaction.response.send_message("Guild is not banned.")
        return

    bot_ban.unban_guild(guild_id)
    
    if bot_ban.is_banned(guild_id, is_guild=True):
        await interaction.response.send_message("Looks like there's an SQL error or something, but the guild isn't banned.")
    else:
        await interaction.response.send_message("Guild has been unbanned successfully.")