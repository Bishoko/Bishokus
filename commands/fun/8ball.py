import nextcord
from nextcord.ext import commands, application_checks
from nextcord.application_command import slash_command, message_command
from utils.get_commands_locales import get_commands_locales
from utils.locale_helpers import CmdLocale, get_slash_option
from utils import config
from utils.settings.bot_ban import check_ban
from utils.languages import text
from utils.settings import prefix
from utils.settings.lang import get_lang

import random

def _ball(lang: str, response_type: str, ask_again: bool):
    if response_type == "evasive":
        response = text(f'8ball_evasive_awnser{random.randint(1, 5-1)}', lang)
    elif response_type == "affirmative":
        response = text(f'8ball_affirmative_awnser{random.randint(1, 8-1)}', lang)
    elif response_type == "negative":
        if lang == "fr" and random.randint(0, 30) == 20:
            response = "Bonsoir non"
        else:
            response = text(f'8ball_negative_awnser{random.randint(1, 5-1)}', lang)

    embed = nextcord.Embed(
        title="🎱 8Ball",
        description=response if not ask_again else text('8ball_no_question', lang),
        color=config.get('embed-color')
    )
    return embed


async def ball(lang: str, message: nextcord.Message):  
    if random.randint(1, 4) == 1:
        response_type = "evasive"
    else:
        response_type = random.choice(["affirmative", "negative"])

    await message.channel.send(
        embed=_ball(lang, response_type, False if message.content else True)
    )

async def ball_slash(lang: str, interaction: nextcord.Interaction, question: str):
    if (random.randint(1, 4) == 1) if question else (random.randint(1, 2) == 1):
        response_type = "evasive"
    else:
        response_type = random.choice(["affirmative", "negative"])

    await interaction.response.send_message(
        embed=_ball(lang, response_type, False)
    )


info = {
    "8ball": {
        "category": "fun",
        "aliases": ["magicball", "8b"],
        "hidden_aliases": ["8-ball", "ball", "balls", "ball8"],
        "available": ["text_command", "context_command"],
        "visibility": "everyone",
        "user_permissions": [],
        "name": "8ball_name",
        "desc": "8ball_desc",
        "args": [
            {
                "name": "8ball_arg_name",
                "desc": "8ball_arg_desc",
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
    @slash_command(
        name=cmd.name,
        description=cmd.description,
        name_localizations=cmd.name_localizations,
        description_localizations=cmd.description_localizations
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