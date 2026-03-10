import nextcord
from nextcord.ext import commands, application_checks
from nextcord.application_command import slash_command, message_command
from utils.logger import log
from utils.get_commands_locales import get_commands_locales
from utils.locale_helpers import CmdLocale, get_slash_option
from utils import config, guild_only
from utils.settings.bot_ban import check_ban
from utils.languages import text
from utils.settings import prefix
from utils.settings.lang import get_lang

import utils.global_variables as gv
from utils.settings import ratio_emoji


async def set_ratio_emoji(lang: str, message: nextcord.Message):
    async def handle_error(e, lang, message):
        emoji = str(e).removeprefix('Unknown emoji: ').removeprefix('Invalid emoji: ')
        
        if emoji in ['up', 'down']:
            await message.reply(
                text('set_ratio_emoji_format_error', lang).replace('%prefix%', prefix.get(message.guild.id)),
                mention_author=False
            )
            return
        
        if str(e).startswith('Unknown emoji'):
            await message.reply(
                text('set_ratio_emoji_unknown_error', lang).replace('%emoji%', emoji),
                mention_author=False
            )
        else:
            await message.reply(
                text('set_ratio_emoji_invalid_error', lang).replace('%emoji%', emoji),
                mention_author=False
            )
    
    async def success(message):
        emoji_up, emoji_down = ratio_emoji.get(message.guild.id, emoji_type='both')
        await message.reply(
            text('set_ratio_emoji_success', lang).replace('%emoji_up%', emoji_up).replace('%emoji_down%', str(emoji_down)),
            mention_author=False
        )
    
    
    if not message.author.guild_permissions.manage_guild:
        await message.reply(text('manage_guild_error', lang), mention_author=False)
        return
    
    content = message.content.split()
    
    if len(content) == 1:
        try:
            ratio_emoji.set(message.guild.id, up_emoji=content[0])
            await success(message)
            return
        except TypeError:
            await handle_error(e, lang, message)
            return
    
    if len(content) != 2:
        await message.reply(
            text('set_ratio_emoji_format_error', lang).replace('%prefix%', prefix.get(message.guild.id)),
            mention_author=False
        )
        return

    emoji_type, emoji = content[0], content[1]
    
    try:
        if emoji_type == 'up':
            ratio_emoji.set(message.guild.id, up_emoji=emoji)
        elif emoji_type == 'down':
            ratio_emoji.set(message.guild.id, down_emoji=emoji)
        else:
            ratio_emoji.set(message.guild.id, up_emoji=content[0], down_emoji=content[1])
    except ValueError as e:
        await handle_error(e, lang, message)
        return
    
    await success(message)

async def set_ratio_emoji_slash(lang: str, interaction: nextcord.Interaction, up_emoji: str = None, down_emoji: str = None):
    try:
        ratio_emoji.set(
            interaction.guild_id,
            client=interaction.client,
            up_emoji=up_emoji,
            down_emoji=down_emoji
        )

        emojis = ratio_emoji.get(interaction.guild_id, interaction.client)
        emojis = (str(emojis[0]), str(emojis[1]))
        
        await interaction.response.send_message(
            text('set_ratio_emoji_success', lang).replace('%emoji_up%', emojis[0]).replace('%emoji_down%', emojis[1])
        )
    except ValueError as e:
        if str(e).startswith('Unknown emoji'):
            await interaction.response.send_message(
                text('set_ratio_emoji_unknown_error', lang).replace('%emoji%', str(e).removeprefix('Unknown emoji: ')),
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                text('set_ratio_emoji_invalid_error', lang).replace('%emoji%', str(e).removeprefix('Invalid emoji: ')),
                ephemeral=True
            )


info = {
    "set_ratio_emoji": {
        "category": "settings",
        "parent": "settings",
        "aliases": ["setratio", "ratio_emoji"],
        "hidden_aliases": ["set_ratio", "ratioemoji", "ratio_emoji", "setraito", "set_ratio", "setratioemoji"],
        "available": ["slash_command", "text_command"],
        "dm_available": False,
        "visibility": "everyone",
        "user_permissions": ["manage_guild"],
        "name": "set_ratio_emoji_name",
        "desc": "set_ratio_emoji_desc",
        "args": [
            {
                "name": "set_ratio_emoji_up_arg_name",
                "desc": "set_ratio_emoji_up_arg_desc",
                "required": False
            },
            {
                "name": "set_ratio_emoji_down_arg_name",
                "desc": "set_ratio_emoji_down_arg_desc",
                "required": False
            }
        ]
    }
}

cmd = CmdLocale(list(info.keys())[0], get_commands_locales(info))

parent = gv.get('bot').get_cog("SettingsCog").settings
class SetRatioEmojiCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @check_ban()
    @guild_only()
    @parent.subcommand(
        name=cmd.name,
        description=cmd.description,
        name_localizations=cmd.name_localizations,
        description_localizations=cmd.description_localizations,
    )
    async def set_ratio_emoji_command(self, interaction: nextcord.Interaction,
        up_emoji: str = get_slash_option(cmd.arg(0)),
        down_emoji: str = get_slash_option(cmd.arg(1))
    ):
        await set_ratio_emoji_slash(get_lang(interaction), interaction, up_emoji, down_emoji)   


def setup(bot: commands.Bot):
    bot.add_cog(SetRatioEmojiCog(bot))

# Text command handler wrapper that adapts to message handler signature
@guild_only()
async def _message_handler(bot, message: nextcord.Message, lang: str, prefix_str: str):
    await set_ratio_emoji(lang, message)
