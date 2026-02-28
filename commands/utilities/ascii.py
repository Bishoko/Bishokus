import nextcord
import pyfiglet
from nextcord.ext import commands, application_checks
from nextcord.application_command import slash_command, message_command
from utils.get_commands_locales import get_commands_locales
from utils.locale_helpers import CmdLocale, get_slash_option
from utils import config
from utils.settings.bot_ban import check_ban
from utils.languages import text
from utils.settings import prefix, lang
get_lang = lang.get_lang


async def ascii_text(lang: str, message: nextcord.Message):
    if message.content == "":
        await message.reply(text('ascii_error_empty_msg', lang), mention_author=False)
        return
    
    if len(message.content) > 13:
        await message.reply(text('ascii_error_length', lang), mention_author=False)
        return

    ascii_art = pyfiglet.figlet_format(message.content)
        
    embed = nextcord.Embed(
        description=f"```\n{ascii_art}```",
        color=nextcord.Color.blurple() 
    )
    
    await message.channel.send(embed=embed)

async def ascii_slash(lang: str, interaction: nextcord.Interaction, content: str):
    if len(content) > 13:
        await interaction.response.send_message(text('ascii_error_length', lang), ephemeral=True)
        return

    ascii_art = pyfiglet.figlet_format(content)

    embed = nextcord.Embed(
        description=f"```\n{ascii_art}```",
        color=nextcord.Color.blurple()
    )

    await interaction.channel.send(embed=embed)


info = {
    "ascii": {
        "category": "utilities",
        "aliases": ["asciify"],
        "hidden_aliases": ["asci"],
        "available": ["slash_command", "text_command"],
        "visibility": "everyone",
        "user_permissions": [],
        "name": "ascii_name",
        "desc": "ascii_desc",
        "args": [
            {
                "name": "ascii_arg_name",
                "desc": "ascii_arg_desc"
            }
        ]
    }
}

cmd = CmdLocale(list(info.keys())[0], get_commands_locales(info))

class AsciiCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @check_ban()
    @application_checks.has_permissions(**{perm: True for perm in cmd.user_permissions})
    @slash_command(
        name=cmd.name,
        description=cmd.description,
        name_localizations=cmd.name_localizations,
        description_localizations=cmd.description_localizations
    )
    async def ascii_command(self, interaction: nextcord.Interaction,
        text: str = get_slash_option(cmd.arg(0))
    ):
        await ascii_slash(get_lang(interaction), interaction, text)


def setup(bot: commands.Bot):
    bot.add_cog(AsciiCog(bot))

# Text command handler wrapper that adapts to message handler signature
async def _message_handler(bot, message: nextcord.Message, lang: str, prefix: str):
    await ascii_text(lang, message)
