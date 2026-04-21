import nextcord
from nextcord.ext import commands, application_checks
from nextcord.application_command import slash_command, message_command
from utils.logger import log
from utils.get_commands_locales import get_commands_locales
from utils.locale_helpers import CmdLocale, get_slash_option
from utils import config, checks
from utils.settings.bot_ban import check_ban
from utils.languages import text
from utils.settings import prefix
from utils.settings.lang import get_lang


async def _clear(count: int, channel, mod: str, lang: str) -> nextcord.Embed:
    await channel.purge(limit=count)
    return (
        text("clear_success", lang)
        .replace("%moderator%", mod)
        .replace("%count%", str(count))
        .replace("%s%", "s" if count > 1 else "")
    )


async def clear_text(lang: str, message: nextcord.Message):
    if not message.content.isnumeric():
        await message.channel.send(text("clear_error_invalid_count", lang))
        return
    
    if message.content == "":
        await message.reply(text('clear_error_invalid_count', lang), mention_author=False)
        return
    
    await message.delete()
    
    await message.channel.send(
        await _clear(int(message.content), message.channel, message.author.display_name, lang) or text("clear_unknown_error", lang),
        delete_after=3
    )

async def clear_slash(lang: str, interaction: nextcord.Interaction, count: int):
    await interaction.channel.send(
        await _clear(count, interaction.channel, interaction.user.display_name, lang) or text("clear_unknown_error", lang),
        delete_after=3
    )
    
    await interaction.response.send_message(
        text("clear_success_slash", lang).replace("%count%", str(count)).replace("%s%", "s" if count > 1 else ""),
        ephemeral=True
    )


info = {
    "clear": {
        "category": "moderation",
        "aliases": ["purge"],
        "hidden_aliases": ["clean", "clr", "cl", "cls",
                           "supprimer", "supprime", "suppr", "effacer", "purger"],
        "available": ["slash_command", "text_command"],
        "visibility": "everyone",
        "bot_permissions": ["manage_messages"],
        "user_permissions": ["manage_messages"],
        "name": "clear_name",
        "desc": "clear_desc",
        "args": [
            {
                "name": "clear_arg_name",
                "desc": "clear_arg_desc",
                "min_value": 1,
                "max_value": 1000,
                "required": True,
            }
        ]
    }
}

cmd = CmdLocale(list(info.keys())[0], get_commands_locales(info))

class ClearCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @check_ban()
    @checks.guild_only()
    @checks.bot_permissions(manage_messages=True)
    @checks.user_permissions(manage_messages=True)
    @slash_command(
        name=cmd.name,
        description=cmd.description,
        name_localizations=cmd.name_localizations,
        description_localizations=cmd.description_localizations,
        default_member_permissions=(nextcord.Permissions(manage_messages=True))
    )
    async def clear_command(self, interaction: nextcord.Interaction,
        count: int = get_slash_option(cmd.arg(0))
    ):
        await clear_slash(get_lang(interaction), interaction, count)


def setup(bot: commands.Bot):
    bot.add_cog(ClearCog(bot))

# Text command handler wrapper that adapts to message handler signature
@checks.guild_only()
@checks.bot_permissions(manage_messages=True)
@checks.user_permissions(manage_messages=True)
async def _message_handler(bot, message: nextcord.Message, lang: str, guild_prefix: str):
    await clear_text(lang, message)
