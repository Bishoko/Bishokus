import nextcord

from utils.languages import text
from utils.settings import ratio_emoji


async def set_ratio_emoji_slash(lang: str, interaction: nextcord.Interaction, up_emoji: str = None, down_emoji: str = None):
    try:
        ratio_emoji.set(
            interaction.guild_id,
            client=interaction.client,
            up_emoji=up_emoji,
            down_emoji=down_emoji
        )

        emojis = ratio_emoji.get(interaction.guild_id, interaction.client)
        emojis = (str(emojis[0]), str(emojis[1]))
        
        await interaction.response.send_message(
            text('set_ratio_emoji_success', lang).replace('%emoji_up%', emojis[0]).replace('%emoji_down%', emojis[1])
        )
    except ValueError as e:
        if str(e).startswith('Unknown emoji'):
            await interaction.response.send_message(
                text('set_ratio_emoji_unknown_error', lang).replace('%emoji%', str(e).removeprefix('Unknown emoji: ')),
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                text('set_ratio_emoji_invalid_error', lang).replace('%emoji%', str(e).removeprefix('Invalid emoji: ')),
                ephemeral=True
            )