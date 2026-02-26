import json
import nextcord
from nextcord.ext import commands, application_checks
from utils.get_commands_locales import get_commands_locales

from commands.fun.roll import roll_dice_slash
from commands.settings.set_prefix import set_prefix_slash
from commands.settings.set_guild_lang import set_guild_lang_slash
from commands.settings.set_ratio_emoji import set_ratio_emoji_slash
from commands.bot_owner.ban_user import bot_ban_user, bot_unban_user
from commands.bot_owner.ban_guild import bot_ban_guild, bot_unban_guild

from utils.settings import prefix, lang
get_lang = lang.get_lang
from utils.settings.bot_ban import check_ban
from utils.languages import get_languages_info

# Load JSON localization data
with open('config/config.json', 'r', encoding='utf-8') as config_file:
    config = json.load(config_file)
    default_locale = config['default-slash-locale']

# simple wrapper objects make the interface more readable for callers
class ArgLocale:
    def __init__(self, data: dict):
        self._d = data

    @property
    def name(self) -> str:
        return self._d['name'][default_locale]

    @property
    def description(self) -> str:
        return self._d['desc'][default_locale]

    @property
    def name_localizations(self) -> dict:
        return self._d['name']

    @property
    def description_localizations(self) -> dict:
        return self._d['desc']

    @property
    def choices(self):
        return self._d.get('choices')

    @property
    def required(self):
        return self._d.get('required', True)

    @property
    def min_length(self):
        return self._d.get('min_length')

    @property
    def max_length(self):
        return self._d.get('max_length')


class CmdLocale:
    def __init__(self, name: str, locales: dict):
        self._d = locales[name]

    @property
    def name(self) -> str:
        return self._d['name'][default_locale]

    @property
    def description(self) -> str:
        return self._d['desc'][default_locale]

    @property
    def name_localizations(self) -> dict:
        return self._d['name']

    @property
    def description_localizations(self) -> dict:
        return self._d['desc']

    @property
    def user_permissions(self) -> list:
        return self._d.get('user_permissions', [])

    def arg(self, index: int) -> ArgLocale:
        return ArgLocale(self._d['args'][index])




def get_slash_option(cmd_or_arg, arg_index=None, locales=None, custom_choices=None):
    """Return a SlashOption for either a (command, index) pair or an ArgLocale.

    Older callers may still pass command name and index; new code should
    provide a previously-created ArgLocale (e.g. `cmd.arg(0)`).
    """

    if isinstance(cmd_or_arg, ArgLocale):
        arg = cmd_or_arg
    else:
        # legacy path: build an ArgLocale from command name and index
        if locales is None:
            locales = get_commands_locales()
        arg = ArgLocale(locales[cmd_or_arg]['args'][arg_index])

    return nextcord.SlashOption(
        name=arg.name,
        name_localizations=arg.name_localizations,
        description=arg.description,
        description_localizations=arg.description_localizations,
        choices=custom_choices or arg.choices,
        required=arg.required,
        min_length=arg.min_length,
        max_length=arg.max_length
    )


def register_slash_commands(bot: commands.Bot):
    locales = get_commands_locales()
    
    
    #  -- BOT_OWNER --
    
    command = 'ban_user'
    cmd = CmdLocale(command, locales)
    @bot.slash_command(
        guild_ids=[config.get('bot-guild'), config.get('testing-guild')],
        name=cmd.name,
        description=cmd.description,
        name_localizations=cmd.name_localizations,
        description_localizations=cmd.description_localizations,
        default_member_permissions=None
    )
    @check_ban()
    @application_checks.is_owner()
    async def bot_ban_user_command(interaction: nextcord.Interaction,
        user: nextcord.User = get_slash_option(cmd.arg(0)),
        ban_type: str = get_slash_option(cmd.arg(1)),
        reason: str = get_slash_option(cmd.arg(2))
    ):
        await bot_ban_user(interaction, user, ban_type, reason)


    command = 'ban_guild'
    cmd = CmdLocale(command, locales)
    @bot.slash_command(
        guild_ids=[config.get('bot-guild'), config.get('testing-guild')],
        name=cmd.name,
        description=cmd.description,
        name_localizations=cmd.name_localizations,
        description_localizations=cmd.description_localizations,
        default_member_permissions=None
    )
    @check_ban()
    @application_checks.is_owner()
    async def bot_ban_guild_command(interaction: nextcord.Interaction,
        guild: str = get_slash_option(cmd.arg(0)),
        type: str = get_slash_option(cmd.arg(1)),
        reason: str = get_slash_option(cmd.arg(2))
    ):
        await bot_ban_guild(interaction, guild, type, reason)
        
        
    command = 'unban_user'
    cmd = CmdLocale(command, locales)
    @bot.slash_command(
        guild_ids=[config.get('bot-guild'), config.get('testing-guild')],
        name=cmd.name,
        description=cmd.description,
        name_localizations=cmd.name_localizations,
        description_localizations=cmd.description_localizations,
        default_member_permissions=None
    )
    @check_ban()
    @application_checks.is_owner()
    async def bot_unban_user_command(interaction: nextcord.Interaction,
        user: nextcord.User = get_slash_option(cmd.arg(0)),
        confirmation: str = get_slash_option(cmd.arg(1))
    ):
        await bot_unban_user(interaction, user, confirmation)


    command = 'unban_guild'
    cmd = CmdLocale(command, locales)
    @bot.slash_command(
        guild_ids=[config.get('bot-guild'), config.get('testing-guild')],
        name=cmd.name,
        description=cmd.description,
        name_localizations=cmd.name_localizations,
        description_localizations=cmd.description_localizations,
        default_member_permissions=None
    )
    @check_ban()
    @application_checks.is_owner()
    async def bot_unban_guild_command(interaction: nextcord.Interaction,
        guild: str = get_slash_option(cmd.arg(0)),
        confirmation: str = get_slash_option(cmd.arg(1))
    ):
        await bot_unban_guild(interaction, guild, confirmation)
    
    
    #  -- CONFIG --
    
    command = 'prefix'
    cmd = CmdLocale(command, locales)
    @bot.slash_command(
        name=cmd.name,
        description=cmd.description,
        name_localizations=cmd.name_localizations,
        description_localizations=cmd.description_localizations,
        default_member_permissions=(nextcord.Permissions(manage_guild=True))
    )
    @check_ban()
    @application_checks.has_permissions(**{perm: True for perm in cmd.user_permissions})
    async def prefix_command(interaction: nextcord.Interaction,
        new_prefix: str = get_slash_option(cmd.arg(0))
    ):
        await set_prefix_slash(get_lang(interaction), interaction, new_prefix)
    
    
    command = 'lang'
    cmd = CmdLocale(command, locales)
    @bot.slash_command(
        name=cmd.name,
        description=cmd.description,
        name_localizations=cmd.name_localizations,
        description_localizations=cmd.description_localizations,
        default_member_permissions=(nextcord.Permissions(manage_guild=True))
    )
    @check_ban()
    @application_checks.has_permissions(**{perm: True for perm in cmd.user_permissions})
    async def language_command(interaction: nextcord.Interaction,
        new_lang: str = get_slash_option(cmd.arg(0), custom_choices={lang["native_name"]: lang["code"] for lang in get_languages_info()})
    ):
        await set_guild_lang_slash(get_lang(interaction), interaction, new_lang)
    
    
    command = 'set_ratio_emoji'
    cmd = CmdLocale(command, locales)
    @bot.slash_command(
        name=cmd.name,
        description=cmd.description,
        name_localizations=cmd.name_localizations,
        description_localizations=cmd.description_localizations,
        default_member_permissions=(nextcord.Permissions(manage_guild=True))
    )
    @check_ban()
    @application_checks.has_permissions(**{perm: True for perm in cmd.user_permissions})
    async def set_ratio_emoji_command(interaction: nextcord.Interaction,
        up_emoji: str = get_slash_option(cmd.arg(0)),
        down_emoji: str = get_slash_option(cmd.arg(1))
    ):
        await set_ratio_emoji_slash(get_lang(interaction), interaction, up_emoji, down_emoji)    
    
    
    #  -- FUN --
    
    command = 'roll'
    cmd = CmdLocale(command, locales)
    @bot.slash_command(
        name=cmd.name,
        description=cmd.description,
        name_localizations=cmd.name_localizations,
        description_localizations=cmd.description_localizations
    )
    @check_ban()
    @application_checks.has_permissions(**{perm: True for perm in cmd.user_permissions})
    async def roll_command(interaction: nextcord.Interaction,
        dice: str = get_slash_option(cmd.arg(0))
    ):
        await roll_dice_slash(get_lang(interaction), prefix.get(interaction.guild_id), interaction, dice)

# Testing
if __name__ == '__main__':
    print(get_commands_locales())
