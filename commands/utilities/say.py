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

# TODO: check for role mentions too in the message content, not just everyone and here
# TODO: Add logging for mentions and content of the message for moderation purposes (can be disabled in config)
# TODO: Option to completely disable mentions in the say command for everyone, here, and roles, with a specific error message for each case
# TODO: Add support for ratioing a message with the say command


async def say_text(lang: str, message: nextcord.Message):
    if ("@everyone" in message.content or "@here" in message.content) and not message.mention_everyone:
        await message.reply(text('say_error_everyone', lang), mention_author=False)
        return
    
    if message.content == "":
        await message.reply(text('say_error_empty_msg', lang), mention_author=False)
        return

    if message.reference:
        base_reply = await message.channel.fetch_message(message.reference.message_id)
        if base_reply:
            print(base_reply.author.id)
            print([m.id for m in message.mentions])
            print(base_reply.author.id in [m.id for m in message.mentions])
            await base_reply.reply(
                message.content,
                mention_author=(base_reply.author.id in [m.id for m in message.mentions])
            )
            return
        
    await message.channel.send(message.content)

async def say_text_slash(lang: str, interaction: nextcord.Interaction, content: str):
    if ("@everyone" in content or "@here" in content) and not interaction.permissions.mention_everyone:
        await interaction.response.send_message(text('say_error_everyone', lang), ephemeral=True)
        return
    
    await interaction.channel.send(content)
    await interaction.response.send_message(text('say_success', lang), ephemeral=True)


info = {
    "say": {
        "category": "utilities",
        "aliases": ["repeat", "echo"],
        "hidden_aliases": ["dire"],
        "available": ["slash_command", "text_command"],
        "visibility": "everyone",
        "user_permissions": [],
        "name": "say_name",
        "desc": "say_desc",
        "args": [
            {
                "name": "say_arg_name",
                "desc": "say_arg_desc"
            }
        ]
    }
}

cmd = CmdLocale(list(info.keys())[0], get_commands_locales(info))

class SayCog(commands.Cog):
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
    async def say_command(self, interaction: nextcord.Interaction,
        text: str = get_slash_option(cmd.arg(0))
    ):
        await say_text_slash(get_lang(interaction), interaction, text)


def setup(bot: commands.Bot):
    bot.add_cog(SayCog(bot))

# Text command handler wrapper that adapts to message handler signature
async def _message_handler(bot, message: nextcord.Message, lang: str, prefix: str):
    await say_text(lang, message)
