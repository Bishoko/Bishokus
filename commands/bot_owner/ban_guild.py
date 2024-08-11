import nextcord

from utils.settings import bot_ban


async def bot_ban_guild(interaction: nextcord.Interaction, guild_id: int, ban_type: str, reason: str):

    bot_ban.ban_guild(guild_id, ban_type, reason)

    await interaction.response.send_message("Guild has been banned successfully.")