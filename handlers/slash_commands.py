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
from utils.settings.bot_ban import check_ban
from utils.languages import get_languages_info

# Load JSON localization data
with open('config/config.json', 'r', encoding='utf-8') as config_file:
    config = json.load(config_file)
    default_locale = config['default-slash-locale']


def get_lang(interaction: nextcord.Interaction) -> str:
    return lang.get_lang(interaction)

def get_slash_option(command, arg_index, locales=None, custom_choices=None):
    if not locales:
        locales = get_commands_locales()
    
    return nextcord.SlashOption(
        name=locales[command]['args'][arg_index]['name'][default_locale],
        name_localizations=locales[command]['args'][arg_index]['name'],
        description=locales[command]['args'][arg_index]['desc'][default_locale],
        description_localizations=locales[command]['args'][arg_index]['desc'],
        choices=custom_choices or locales[command]['args'][arg_index].get('choices'),
        required=locales[command]['args'][arg_index].get('required', True),
        min_length=locales[command]['args'][arg_index].get('min_length'),
        max_length=locales[command]['args'][arg_index].get('max_length')
    )


def register_slash_commands(bot: commands.Bot):
    locales = get_commands_locales()
    
    
    #  -- BOT_OWNER --
    
    command = 'ban_user'
    @bot.slash_command(
        guild_ids=[config.get('bot-guild'), config.get('testing-guild')],
        name=locales[command]['name'][default_locale],
        description=locales[command]['desc'][default_locale],
        name_localizations=locales[command]['name'],
        description_localizations=locales[command]['desc'],
        default_member_permissions=None
    )
    @check_ban()
    @application_checks.is_owner()
    async def bot_ban_user_command(interaction: nextcord.Interaction,
        user: nextcord.User = get_slash_option('ban_user', 0),
        ban_type: str = get_slash_option('ban_user', 1),
        reason: str = get_slash_option('ban_user', 2)
    ):
        await bot_ban_user(interaction, user, ban_type, reason)


    command = 'ban_guild'
    @bot.slash_command(
        guild_ids=[config.get('bot-guild'), config.get('testing-guild')],
        name=locales[command]['name'][default_locale],
        description=locales[command]['desc'][default_locale],
        name_localizations=locales[command]['name'],
        description_localizations=locales[command]['desc'],
        default_member_permissions=None
    )
    @check_ban()
    @application_checks.is_owner()
    async def bot_ban_guild_command(interaction: nextcord.Interaction,
        guild: str = get_slash_option('ban_guild', 0),
        type: str = get_slash_option('ban_guild', 1),
        reason: str = get_slash_option('ban_guild', 2)
    ):
        await bot_ban_guild(interaction, guild, type, reason)
        
        
    command = 'unban_user'
    @bot.slash_command(
        guild_ids=[config.get('bot-guild'), config.get('testing-guild')],
        name=locales[command]['name'][default_locale],
        description=locales[command]['desc'][default_locale],
        name_localizations=locales[command]['name'],
        description_localizations=locales[command]['desc'],
        default_member_permissions=None
    )
    @check_ban()
    @application_checks.is_owner()
    async def bot_unban_user_command(interaction: nextcord.Interaction,
        user: nextcord.User = get_slash_option('unban_user', 0),
        confirmation: str = get_slash_option('unban_user', 1)
    ):
        await bot_unban_user(interaction, user, confirmation)


    command = 'unban_guild'
    @bot.slash_command(
        guild_ids=[config.get('bot-guild'), config.get('testing-guild')],
        name=locales[command]['name'][default_locale],
        description=locales[command]['desc'][default_locale],
        name_localizations=locales[command]['name'],
        description_localizations=locales[command]['desc'],
        default_member_permissions=None
    )
    @check_ban()
    @application_checks.is_owner()
    async def bot_unban_guild_command(interaction: nextcord.Interaction,
        guild: str = get_slash_option('unban_guild', 0),
        confirmation: str = get_slash_option('unban_guild', 1)
    ):
        await bot_unban_guild(interaction, guild, confirmation)
    
    
    #  -- CONFIG --
    
    command = 'prefix'
    @bot.slash_command(
        name=locales[command]['name'][default_locale],
        description=locales[command]['desc'][default_locale],
        name_localizations=locales[command]['name'],
        description_localizations=locales[command]['desc'],
        default_member_permissions=(nextcord.Permissions(manage_guild=True))
    )
    @check_ban()
    @application_checks.has_permissions(**{perm: True for perm in locales[command].get('user_permissions', [])})
    async def prefix_command(interaction: nextcord.Interaction,
        new_prefix: str = get_slash_option('prefix', 0)
    ):
        await set_prefix_slash(get_lang(interaction), interaction, new_prefix)
    
    
    command = 'lang'
    @bot.slash_command(
        name=locales[command]['name'][default_locale],
        description=locales[command]['desc'][default_locale],
        name_localizations=locales[command]['name'],
        description_localizations=locales[command]['desc'],
        default_member_permissions=(nextcord.Permissions(manage_guild=True))
    )
    @check_ban()
    @application_checks.has_permissions(**{perm: True for perm in locales[command].get('user_permissions', [])})
    async def language_command(interaction: nextcord.Interaction,
        new_lang: str = get_slash_option('lang', 0, custom_choices={lang["native_name"]: lang["code"] for lang in get_languages_info()})
    ):
        await set_guild_lang_slash(get_lang(interaction), interaction, new_lang)
    
    
    command = 'set_ratio_emoji'
    @bot.slash_command(
        name=locales[command]['name'][default_locale],
        description=locales[command]['desc'][default_locale],
        name_localizations=locales[command]['name'],
        description_localizations=locales[command]['desc'],
        default_member_permissions=(nextcord.Permissions(manage_guild=True))
    )
    @check_ban()
    @application_checks.has_permissions(**{perm: True for perm in locales[command].get('user_permissions', [])})
    async def set_ratio_emoji_command(interaction: nextcord.Interaction,
        up_emoji: str = get_slash_option('set_ratio_emoji', 0),
        down_emoji: str = get_slash_option('set_ratio_emoji', 1)
    ):
        await set_ratio_emoji_slash(get_lang(interaction), interaction, up_emoji, down_emoji)    
    
    
    #  -- FUN --
    
    command = 'roll'
    @bot.slash_command(
        name=locales[command]['name'][default_locale],
        description=locales[command]['desc'][default_locale],
        name_localizations=locales[command]['name'],
        description_localizations=locales[command]['desc']
    )
    @check_ban()
    @application_checks.has_permissions(**{perm: True for perm in locales[command].get('user_permissions', [])})
    async def roll_command(interaction: nextcord.Interaction,
        dice: str = get_slash_option('roll', 0)
    ):
        await roll_dice_slash(get_lang(interaction), prefix.get(interaction.guild_id), interaction, dice)

# Testing
if __name__ == '__main__':
    print(get_commands_locales())