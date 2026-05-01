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


def _length(input: str, lang: str) -> str:
    input = input.strip()
    # Prevent code block injection if the user tries to inject a code block with mentions
    input = input.replace("```", "") if "```" in input and "@" in input else input
    
    output = [
        text("length_output_l1", lang),
        text("length_output_l2", lang).replace('%string%', str(input) if input else " "),
        text("length_output_l3", lang).replace('%length%', str(len(input))),
        text("length_output_l4", lang).replace('%length_no_spaces%', str(len(input.replace(" ", "")))),
        text("length_output_l5", lang).replace('%space_length%', str(input.count(" "))),
    ]
    
    return "\n".join(output)


async def length_text(lang: str, message: nextcord.Message):
    await message.reply(
        _length(message.content, lang),
        mention_author=False
    )

async def length_slash(lang: str, interaction: nextcord.Interaction, content: str):
    await interaction.response.send_message(
        _length(content, lang),
        ephemeral=False
    )


info = {
    "length": {
        "category": "utilities",
        "aliases": [],
        "hidden_aliases": ["l", "len", "longueur", "long", "taille",
                           "mesurer", "measure", "compte", "compter", "count"],
        "available": ["slash_command", "text_command"],
        "visibility": "everyone",
        "user_permissions": [],
        "name": "length_name",
        "desc": "length_desc",
        "args": [
            {
                "name": "length_arg_name",
                "desc": "length_arg_desc"
            }
        ]
    }
}

cmd = CmdLocale(list(info.keys())[0], get_commands_locales(info))

class LengthCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @check_ban()
    @slash_command(
        name=cmd.name,
        description=cmd.description,
        name_localizations=cmd.name_localizations,
        description_localizations=cmd.description_localizations
    )
    async def length_command(self, interaction: nextcord.Interaction,
        text: str = get_slash_option(cmd.arg(0))
    ):
        await length_slash(get_lang(interaction), interaction, text)


def setup(bot: commands.Bot):
    bot.add_cog(LengthCog(bot))

# Text command handler wrapper that adapts to message handler signature
async def _message_handler(bot, message: nextcord.Message, lang: str, guild_prefix: str):
    await length_text(lang, message)
