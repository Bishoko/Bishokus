import nextcord

from utils.settings import bot_ban


async def bot_ban_guild(interaction: nextcord.Interaction, guild_id: int, ban_type: str, reason: str):
    guild = interaction.client.get_guild(int(guild_id))
    guild_name = guild.name if guild else "Unknown Guild"

    bot_ban.ban_guild(guild_id, ban_type, reason)

    await interaction.response.send_message(
        f"Guild `{guild_name} ({guild_id})` has been banned successfully.\n" \
        f"Owner: `{guild.owner.name} ({guild.owner_id})`\n" \
        f"\n" \
        f"Reason: `{reason}`\n" \
    )
    
    
async def bot_unban_guild(interaction: nextcord.Interaction, guild_id: int, confirmation: str):
    if confirmation.lower() != 'yes':
        await interaction.response.send_message("Unban operation cancelled.")
        return

    if not bot_ban.is_banned(guild_id, is_guild=True):
        await interaction.response.send_message("Guild is not banned.")
        return

    guild = interaction.client.get_guild(int(guild_id))
    guild_name = guild.name if guild else "Unknown Guild"

    bot_ban.unban_guild(guild_id)
    
    if bot_ban.is_banned(guild_id, is_guild=True):
        await interaction.response.send_message(f"Looks like there's an SQL error or something, but the guild `{guild_name} ({guild_id})` isn't banned.")
    else:
        await interaction.response.send_message(f"Guild `{guild_name} ({guild_id})` has been unbanned successfully.\nOwner: `{guild.owner.name} ({guild.owner_id})`")