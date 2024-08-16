import nextcord
import random
from utils.languages import text
from utils.get_user_nickname import get_nickname


async def ratio(message: nextcord.Message):
    await message.add_reaction('👍')
    
    try:
        target_message = await message.channel.fetch_message(message.reference.message_id)
        await target_message.add_reaction('👍')
    except AttributeError:
        pass


async def ratio_context(lang: str, interaction: nextcord.Interaction, original_message: nextcord.Message):
    await original_message.add_reaction('👍')
    
    embed = nextcord.Embed(
        title=text(f'ratio_context_title{random.randint(1, 9)}', lang),
        description=text('ratio_context_description', lang).replace(
                         '%original_author%', original_message.author.mention).replace(
                         '%interaction_user%', interaction.user.mention),
                    # + '\n\n' + text('ratio_context_original_message', lang) + ':\n' +
                    # f"*[{text('ratio_context_see_original_message', lang)}]({original_message.jump_url})*",
        color=0xae10ff
    )
    # embed.add_field(
    #     name=f'{get_nickname(original_message.author)}',
    #     value=f'{original_message.content}',
    #     inline=False
    # )
    
    if original_message.attachments:
        view = nextcord.ui.View()
        view.add_item(nextcord.ui.Button(
            label=text('ratio_context_button_label', lang).replace('%attachment_count%', len(original_message.attachments)),
            url=original_message.jump_url
        ))
        sent_message = await original_message.reply(embed=embed, view=view, mention_author=False)
    else:
        sent_message = await original_message.reply(embed=embed, mention_author=False)
    
    await sent_message.add_reaction('👍')
    await sent_message.add_reaction('👎')
    
    await interaction.response.send_message(
        text('ratio_context_confirmation', lang),
        ephemeral=True
    )
    