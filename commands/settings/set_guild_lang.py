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

from utils.languages import get_languages_info


async def set_guild_lang(lang: str, message: nextcord.Message):
    if message.author.guild_permissions.manage_guild == False:
        await message.reply(text('manage_guild_error', lang), mention_author=False)
        return
    
    lang_codes = [lang["code"] for lang in get_languages_info()]
    
    new_lang = message.content.lower().replace('anglais', 'en')
    new_lang = next((l for l in lang_codes if l.lower().startswith(new_lang[:2])), '')
    
    # Check if the user provided a new language
    if not message.content.replace('-','').replace('_',''):
        current_lang = lang.get_guild(message.guild.id)
        p = prefix.get(message.guild.id)
        await message.reply(
            text('set_guild_lang_empty_error', lang).replace('%current_lang%', current_lang).replace('%prefix%', p),
            mention_author=False
        )
        return
    
    
    if new_lang not in lang_codes:
        await message.reply(
            text('set_guild_lang_error', lang).replace(
                '%new_lang%', message.content.lower()).replace(
                '%available_langs%', '`'+f'` {text("or", lang).strip()} `'.join(lang_codes)+'`'
            ),
            mention_author=False
        )
        return
    
    lang.set_guild(message.guild.id, new_lang.lower())
    
    await message.reply(
        text('set_guild_lang_success', new_lang).replace('%new_lang%', new_lang),
        mention_author=False
    )


async def set_guild_lang_slash(lang: str, interaction: nextcord.Interaction, new_lang: str):
    lang_codes = [lang["code"] for lang in get_languages_info()]
    
    if new_lang not in lang_codes:
        await interaction.response.send_message(
            text('set_guild_lang_error', lang).replace('%new_lang%', new_lang).replace(
                '%available_langs%', '`'+f'` {text("or", lang).strip()} `'.join(lang_codes)+'`'
            )
        )
        return
    
    lang.set_guild(interaction.guild_id, new_lang.lower())
    
    await interaction.response.send_message(
        text('set_guild_lang_success', new_lang).replace('%new_lang%', new_lang)
    )



info = {
    "lang": {
        "category": "settings",
        "aliases": ["language", "setlang", "setlanguage", "serverlang", "serverlanguage"],
        "hidden_aliases": ["setserverlang", "setserverlanguage", "set_serverlang", "set_server_lang", "setguildlang", "set_guildlang", "set_guild_lang", "guild_lang", "guildlang"],
        "available": ["slash_command", "text_command"],
        "visibility": "everyone",
        "user_permissions": ["manage_guild"],
        "name": "language_name",
        "desc": "language_desc",
        "args": [
            {
                "name": "language_arg_name",
                "desc": "language_arg_desc"
            }
        ]
    },
}

cmd = CmdLocale(list(info.keys())[0], get_commands_locales(info))

class LangCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @check_ban()
    @application_checks.has_permissions(**{perm: True for perm in cmd.user_permissions})
    @slash_command(
        name=cmd.name,
        description=cmd.description,
        name_localizations=cmd.name_localizations,
        description_localizations=cmd.description_localizations,
        default_member_permissions=(nextcord.Permissions(manage_guild=True))
    )
    async def language_command(self, interaction: nextcord.Interaction,
        new_lang: str = get_slash_option(cmd.arg(0), custom_choices={lang["native_name"]: lang["code"] for lang in get_languages_info()})
    ):
        await set_guild_lang_slash(get_lang(interaction), interaction, new_lang)


def setup(bot: commands.Bot):
    bot.add_cog(LangCog(bot))

# Text command handler wrapper that adapts to message handler signature
async def _message_handler(bot, message: nextcord.Message, lang_str: str, prefix_str: str):
    await set_guild_lang(lang_str, message)
