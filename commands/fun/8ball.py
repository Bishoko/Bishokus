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


async def ball(lang: str, message: nextcord.Message):  
    if not message.content: 
        await message.reply(text('ball_error_no_question', lang), mention_author=False)
        return

    random_list = random.randint(1, 4)
    if random_list == 1:
        type = "evasive"
    else:
        random_list_2 = random.randint(1,2)
        if random_list_2 == 1:
            type = "affirmative"
        if random_list_2 == 2:
            type = "negative"

    if type == "evasive":
        response = text(f'evasive_awnser{random.randint(1, 5)}', lang)
    elif type == "affirmative":
        response = text(f'affirmative_awnser{random.randint(1, 8)}', lang)
    elif type == "negative":
        random_bonsoirnon = 0
        if lang == "fr":
            random_bonsoirnon = random.randint(0, 30)
        if random_bonsoirnon == 20:
            response = "Bonsoir non"
        else:
            response = text(f'negative_awnser{random.randint(1, 8)}', lang)

    embed = nextcord.Embed(
        title="🎱 8Ball",
        description=response,
        color=config.get('embed-color')
    )
    await message.channel.send(embed=embed)


async def ball_slash(lang: str, interaction: nextcord.Interaction, question: str):
    if not question:
        await interaction.response.send_message(text('ball_error_no_question', lang), ephemeral=True)
        return

    random_list = random.randint(1, 4)
    if random_list == 1:
        type = "evasive"
    else:
        random_list_2 = random.randint(1,2)
        if random_list_2 == 1:
            type = "affirmative"
        if random_list_2 == 2:
            type = "negative"

    if type == "evasive":
        response = text(f'evasive_awnser{random.randint(1, 5)}', lang)
    elif type == "affirmative":
        response = text(f'affirmative_awnser{random.randint(1, 8)}', lang)
    elif type == "negative":
        random_bonsoirnon = 0
        if lang == "fr":
            random_bonsoirnon = random.randint(0, 30)
        if random_bonsoirnon == 20:
            response = "Bonsoir non"
        else:
            response = text(f'negative_awnser{random.randint(1, 8)}', lang)

    embed = nextcord.Embed(
        title="🎱 8Ball",
        description=response,
        color=config.get('embed-color')
    )
    await interaction.response.send_message(embed=embed)


info = {
    "8ball": {
        "category": "fun",
        "aliases": [],
        "hidden_aliases": ["ball", "balls", "ball8"],
        "available": ["text_command", "context_command"],
        "visibility": "everyone",
        "user_permissions": [],
        "name": "ball_name",
        "desc": "ball_desc",
        "args": [
            {
                "name": "ball_arg_name",
                "desc": "ball_arg_desc",
                "required": False
            }
        ]
    },
}

cmd = CmdLocale(list(info.keys())[0], get_commands_locales(info))

class ballCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @check_ban()
    @message_command(
        name=cmd.name,
        name_localizations=cmd.name_localizations
    )
    async def ball_command(self, interaction: nextcord.Interaction,
        question: str = get_slash_option(cmd.arg(0))
    ):
        await ball_slash(get_lang(interaction), interaction, question)


def setup(bot: commands.Bot):
    bot.add_cog(ballCog(bot))

# Text command handler wrapper that adapts to message handler signature
async def _message_handler(bot, message: nextcord.Message, lang: str, prefix: str):
    await ball(lang, message)