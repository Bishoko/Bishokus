import nextcord

from utils.settings import bot_ban


async def bot_ban_user(interaction: nextcord.Interaction, user: nextcord.User, ban_type: str, reason: str):

    bot_ban.ban_user(user.id, ban_type, reason)
    await interaction.response.send_message(f"User `{user.name} ({user.id})` has been banned successfully.")    
    
    
async def bot_unban_user(interaction: nextcord.Interaction, user: nextcord.User, confirmation: str):
    if confirmation.lower() != 'yes':
        await interaction.response.send_message(f"Unban operation for `{user.name} ({user.id})` cancelled.")
        return

    if not bot_ban.is_banned(user.id):
        await interaction.response.send_message(f"User `{user.name} ({user.id})` is not banned.")
        return

    bot_ban.unban_user(user.id)
    
    if bot_ban.is_banned(user.id):
        await interaction.response.send_message(f"Looks like there's an SQL error or something, but `{user.name} ({user.id})` isn't banned.")
    else:
        await interaction.response.send_message(f"User `{user.name} ({user.id})` has been unbanned successfully.")