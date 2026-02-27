import nextcord
from nextcord.ext import commands, application_checks
from nextcord.application_command import slash_command, message_command
from utils.get_commands_locales import get_commands_locales
from utils.locale_helpers import CmdLocale, get_slash_option
from utils import config
from utils.settings.bot_ban import check_ban
from utils.languages import text
from utils.settings import prefix, lang
get_lang = lang.get_lang

import random
from utils.settings import ratio_emoji
from utils.get_user_nickname import get_nickname


async def ratio(client, message: nextcord.Message):
    up_emoji = ratio_emoji.get(message.guild.id, client, 'up')[0]
    await message.add_reaction(up_emoji)
    
    try:
        target_message = await message.channel.fetch_message(message.reference.message_id)
        await target_message.add_reaction(up_emoji)
    except AttributeError:
        pass


async def ratio_context(lang: str, interaction: nextcord.Interaction, original_message: nextcord.Message):
    emojis = ratio_emoji.get(interaction.guild_id, interaction.client)
    up_emoji, down_emoji = emojis[0], emojis[1]
    
    await original_message.add_reaction(up_emoji)
    
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
    
    await sent_message.add_reaction(up_emoji)
    await sent_message.add_reaction(down_emoji)
    
    await interaction.response.send_message(
        text('ratio_context_success', lang),
        ephemeral=True
    )


info = {
    "ratio": {
        "category": "fun",
        "aliases": [],
        "hidden_aliases": ["raito"],
        "available": ["text_command", "context_command"],
        "visibility": "everyone",
        "user_permissions": [],
        "name": "ratio_name",
        "desc": "ratio_desc",
        "args": [
            {
                "name": "ratio_arg_name",
                "desc": "ratio_arg_desc",
                "required": False
            }
        ]
    },
}

cmd = CmdLocale(list(info.keys())[0], get_commands_locales(info))

class RatioCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @check_ban()
    @message_command(
        name=cmd.name,
        name_localizations=cmd.name_localizations
    )
    async def ratio_context_command(self, interaction: nextcord.Interaction, message: nextcord.Message):
        await ratio_context(get_lang(interaction), interaction, message)


def setup(bot: commands.Bot):
    bot.add_cog(RatioCog(bot))

# Text command handler wrapper that adapts to message handler signature
async def _message_handler(bot, message: nextcord.Message, lang: str, prefix: str):
    await ratio(bot, message)
