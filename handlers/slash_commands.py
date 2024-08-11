import json
import nextcord
from nextcord.ext import commands, application_checks
from utils.get_commands_locales import get_commands_locales

from commands.roll import roll_dice_slash
from commands.settings.set_prefix import set_prefix_slash
from commands.settings.set_guild_lang import set_guild_lang_slash
from commands.bot_owner.ban_user import bot_ban_user
from commands.bot_owner.ban_guild import bot_ban_guild

from utils.settings import prefix, lang
from utils.languages import get_languages_info

# Load JSON localization data
with open('config/config.json', 'r', encoding='utf-8') as config_file:
    config = json.load(config_file)
    default_locale = config['default-slash-locale']


def get_lang(interaction: nextcord.Interaction) -> str:
    return lang.get(interaction.guild_id, interaction.user.id)


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
    @application_checks.is_owner()
    async def bot_ban_user_command(interaction: nextcord.Interaction,
        user: nextcord.User = nextcord.SlashOption(
            name=locales[command]['args'][0]['name'][default_locale],
            name_localizations=locales[command]['args'][0]['name'],
            description=locales[command]['args'][0]['desc'][default_locale],
            description_localizations=locales[command]['args'][0]['desc']
        ),
        ban_type: str = nextcord.SlashOption(
            name=locales[command]['args'][1]['name'][default_locale],
            name_localizations=locales[command]['args'][1]['name'],
            description=locales[command]['args'][1]['desc'][default_locale],
            description_localizations=locales[command]['args'][1]['desc'],
            choices=locales[command]['args'][1]['choices']
        ),
        reason: str = nextcord.SlashOption(
            name=locales[command]['args'][2]['name'][default_locale],
            name_localizations=locales[command]['args'][2]['name'],
            description=locales[command]['args'][2]['desc'][default_locale],
            description_localizations=locales[command]['args'][2]['desc'],
            required=False
        )
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
    @application_checks.is_owner()
    async def bot_ban_guild_command(interaction: nextcord.Interaction,
        guild: str = nextcord.SlashOption(
            name=locales[command]['args'][0]['name'][default_locale],
            name_localizations=locales[command]['args'][0]['name'],
            description=locales[command]['args'][0]['desc'][default_locale],
            description_localizations=locales[command]['args'][0]['desc']
        ),
        type: str = nextcord.SlashOption(
            name=locales[command]['args'][1]['name'][default_locale],
            name_localizations=locales[command]['args'][1]['name'],
            description=locales[command]['args'][1]['desc'][default_locale],
            description_localizations=locales[command]['args'][1]['desc'],
            choices=locales[command]['args'][1]['choices']
        ),
        reason: str = nextcord.SlashOption(
            name=locales[command]['args'][2]['name'][default_locale],
            name_localizations=locales[command]['args'][2]['name'],
            description=locales[command]['args'][2]['desc'][default_locale],
            description_localizations=locales[command]['args'][2]['desc'],
            required=False
        )
    ):
        await bot_ban_guild(interaction, guild, type, reason)
    
    
    #  -- CONFIG --
    
    command = 'prefix'
    @bot.slash_command(
        name=locales[command]['name'][default_locale],
        description=locales[command]['desc'][default_locale],
        name_localizations=locales[command]['name'],
        description_localizations=locales[command]['desc'],
        default_member_permissions=(nextcord.Permissions(manage_guild=True))
    )
    @application_checks.has_permissions(**{perm: True for perm in locales[command].get('permissions', [])})
    async def prefix_command(interaction: nextcord.Interaction,
        new_prefix: str = nextcord.SlashOption(
            name=locales[command]['args'][0]['name'][default_locale],
            name_localizations=locales[command]['args'][0]['name'],
            description=locales[command]['args'][0]['desc'][default_locale],
            description_localizations=locales[command]['args'][0]['desc'],
            min_length=1,
            max_length=10
        )
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
    @application_checks.has_permissions(**{perm: True for perm in locales[command].get('permissions', [])})
    async def language_command(interaction: nextcord.Interaction,
        new_lang: str = nextcord.SlashOption(
            name=locales[command]['args'][0]['name'][default_locale],
            name_localizations=locales[command]['args'][0]['name'],
            description=locales[command]['args'][0]['desc'][default_locale],
            description_localizations=locales[command]['args'][0]['desc'],
            choices={lang["native_name"]: lang["code"] for lang in get_languages_info()}
        )
    ):
        await set_guild_lang_slash(get_lang(interaction), interaction, new_lang)
    
    
    #  -- FUN --
    
    command = 'roll'
    @bot.slash_command(
        name=locales[command]['name'][default_locale],
        description=locales[command]['desc'][default_locale],
        name_localizations=locales[command]['name'],
        description_localizations=locales[command]['desc']
    )
    @application_checks.has_permissions(**{perm: True for perm in locales[command].get('permissions', [])})
    async def roll_command(interaction: nextcord.Interaction,
        dice: str = nextcord.SlashOption(
            name=locales[command]['args'][0]['name'][default_locale],
            name_localizations=locales[command]['args'][0]['name'],
            description=locales[command]['args'][0]['desc'][default_locale],
            description_localizations=locales[command]['args'][0]['desc']
        )
    ):
        await roll_dice_slash(get_lang(interaction), prefix.get(interaction.guild_id), interaction, dice)

# Testing
if __name__ == '__main__':
    print(get_commands_locales())