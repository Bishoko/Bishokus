import nextcord
from nextcord.ext import commands, application_checks
from nextcord.application_command import slash_command, message_command
from utils.logger import log
from utils.get_commands_locales import get_commands_locales
from utils.locale_helpers import CmdLocale, get_slash_option
from utils import config
from utils.settings.bot_ban import check_ban
from utils.languages import text
from utils.settings import prefix
from utils.settings.lang import get_lang

import random


async def roll_dice(lang: str, prefix, message: nextcord.Message):
    try:
        rolls, limit = map(int, message.content.split('d'))
    except ValueError:
        await message.channel.send(
            text('roll_format_error', lang).replace('%prefix%', prefix)
        )
        return

    result = ', '.join(str(random.randint(1, limit)) for _ in range(rolls))
    await message.reply(result, mention_author=False)

async def roll_dice_slash(lang: str, prefix, interaction: nextcord.Interaction, dice: str):
    try:
        rolls, limit = map(int, dice.split('d'))
    except ValueError:
        await interaction.response.send_message(
            text('roll_format_error', lang).replace('%prefix%', prefix),
            ephemeral=True
        )
        return

    result = ', '.join(str(random.randint(1, limit)) for _ in range(rolls))
    await interaction.response.send_message(result)


info = {
    "roll": {
        "category": "fun",
        "aliases": ["dice", "diceroll", "rolldice"],
        "hidden_aliases": ["dice_roll", "roll_dice"],
        "available": ["slash_command", "text_command"],
        "visibility": "everyone",
        "user_permissions": [],
        "name": "roll_name",
        "desc": "roll_desc",
        "args": [
            {
                "name": "roll_arg_name",
                "desc": "roll_arg_desc"
            }
        ]
    }
}

cmd = CmdLocale(list(info.keys())[0], get_commands_locales(info))

class RollCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @check_ban()
    @slash_command(
        name=cmd.name,
        description=cmd.description,
        name_localizations=cmd.name_localizations,
        description_localizations=cmd.description_localizations
    )
    async def roll_command(self, interaction: nextcord.Interaction,
        dice: str = get_slash_option(cmd.arg(0))
    ):
        await roll_dice_slash(get_lang(interaction), prefix.get(interaction.guild_id), interaction, dice)


def setup(bot: commands.Bot):
    bot.add_cog(RollCog(bot))

# Text command handler wrapper that adapts to message handler signature
async def _message_handler(bot, message: nextcord.Message, lang: str, guild_prefix: str):
    await roll_dice(lang, guild_prefix, message)
