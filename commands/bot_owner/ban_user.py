import nextcord

from utils.settings import bot_ban


async def bot_ban_user(interaction: nextcord.Interaction, user: nextcord.User, ban_type: str, reason: str):

    bot_ban.ban_user(user.id, ban_type, reason)

    await interaction.response.send_message("User has been banned successfully.")
    
    
async def bot_unban_user(interaction: nextcord.Interaction, user: int, confirmation: str):
    if confirmation.lower() != 'yes':
        await interaction.response.send_message("Unban operation cancelled.")
        return

    if not bot_ban.is_banned(user.id):
        await interaction.response.send_message("User is not banned.")
        return

    bot_ban.unban_user(user.id)
    
    if bot_ban.is_banned(user.id):
        await interaction.response.send_message("Looks like there's an SQL error or something, but the user isn't banned.")
    else:
        await interaction.response.send_message("User has been unbanned successfully.")