import nextcord

from utils.languages import text
from utils.settings import ratio_emoji, prefix



async def set_ratio_emoji(lang: str, message: nextcord.Message):
    if not message.author.guild_permissions.manage_guild:
        await message.reply(text('manage_guild_error', lang), mention_author=False)
        return
    
    content = message.content.split()
    if len(content) != 2:
        await message.reply(
            text('set_ratio_emoji_format_error', lang).replace('%prefix%', prefix.get(message.guild.id)),
            mention_author=False
        )
        return

    emoji_type, emoji_id = content[0], content[1]
    
    if emoji_type not in ['up', 'down']:
        await message.reply(text('set_ratio_emoji_format_error', lang), mention_author=False)
        return
    
    try:
        if emoji_type == 'up':
            ratio_emoji.set(message.guild.id, up_emoji=emoji_id)
        else:
            ratio_emoji.set(message.guild.id, down_emoji=emoji_id)
    except ValueError as e:
        if str(e).startswith('Unknown emoji'):
            await message.reply(
                text('set_ratio_emoji_unknown_error', lang).replace('%emoji%', str(e).removeprefix('Unknown emoji: ')),
                mention_author=False
            )
        else:
            await message.reply(
                text('set_ratio_emoji_invalid_error', lang).replace('%emoji%', str(e).removeprefix('Invalid emoji: ')),
                mention_author=False
            )
        return
    
    await message.reply(
        text('set_ratio_emoji_success', lang).replace('%emoji_type%', emoji_type).replace('%emoji_id%', str(emoji_id)),
        mention_author=False
    )

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