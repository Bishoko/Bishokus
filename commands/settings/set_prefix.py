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

import utils.global_variables as gv
from utils.settings import prefix


async def set_prefix(lang: str, message: nextcord.Message):
    if message.author.guild_permissions.manage_guild == False:
        await message.reply(text('manage_guild_error', lang),mention_author=False)
        return
    
    if '`' in message.content:
        await message.reply(
            text('prefix_wrong_char_error', lang).replace('%prefix%', message.content),
            mention_author=False
        )
        return
    
    if len(message.content) > 20:
        await message.reply(text('prefix_length_error', lang))
        return
    
    if len(message.content) == 0:
        await message.reply(text('prefix_empty_error', lang), mention_author=False)
        return
    
    
    prefix.set(message.guild.id, message.content)
    
    await message.reply(
        text('prefix_success', lang).replace('%prefix%', message.content),
        mention_author=False
    )


async def set_prefix_slash(lang: str, interaction: nextcord.Interaction, new_prefix: str):
    
    if '`' in new_prefix:
        await interaction.response.send_message(
            text('prefix_wrong_char_error', lang).replace('%prefix%', new_prefix)
        )
        return
    
    if len(new_prefix) > 20:
        await interaction.response.send_message(text('prefix_length_error', lang))
        return
    
    if len(new_prefix) == 0:
        await interaction.response.send_message(text('prefix_empty_error', lang))
        return
    
    
    prefix.set(interaction.guild_id, new_prefix)
    
    await interaction.response.send_message(
        text('prefix_success', lang).replace('%prefix%', new_prefix)
    )


info = {
    "prefix": {
        "category": "settings",
        "parent": "settings",
        "aliases": ["setprefix", "set_prefix"],
        "hidden_aliases": "",
        "available": ["slash_command", "text_command"],
        "visibility": "everyone",
        "user_permissions": ["manage_guild"],
        "name": "prefix_name",
        "desc": "prefix_desc",
        "args": [
            {
                "name": "prefix_arg_name",
                "desc": "prefix_arg_desc",
                "required": True,
                "min_length": 1,
                "max_length": 10
            }
        ]
    },
}

cmd = CmdLocale(list(info.keys())[0], get_commands_locales(info))

parent = gv.get('bot').get_cog("SettingsCog").settings
class PrefixCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @check_ban()
    @application_checks.has_permissions(**{perm: True for perm in cmd.user_permissions})
    @parent.subcommand(
        name=cmd.name,
        description=cmd.description,
        name_localizations=cmd.name_localizations,
        description_localizations=cmd.description_localizations,
    )
    async def set_prefix_command(self, interaction: nextcord.Interaction,
        new_prefix: str = get_slash_option(cmd.arg(0))
    ):
        await set_prefix_slash(get_lang(interaction), interaction, new_prefix)


def setup(bot: commands.Bot):
    bot.add_cog(PrefixCog(bot))

# Text command handler wrapper that adapts to message handler signature
async def _message_handler(bot, message: nextcord.Message, lang: str, prefix_str: str):
    await set_prefix(lang, message)
