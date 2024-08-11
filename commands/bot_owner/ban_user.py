import nextcord

from utils.settings import bot_ban


async def bot_ban_user(interaction: nextcord.Interaction, user: nextcord.User, ban_type: str, reason: str):

    bot_ban.ban_user(user.id, ban_type, reason)

    await interaction.response.send_message("User has been banned successfully.")