import nextcord
from nextcord.ext import commands, application_checks
from nextcord.application_command import slash_command, message_command
from utils.get_commands_locales import get_commands_locales
from utils.locale_helpers import CmdLocale, get_slash_option
from utils import config
from utils.settings.bot_ban import check_ban
from utils.languages import text
from utils.settings import prefix
from utils.settings.lang import get_lang

from utils.get_user import get_user

class AvatarView(nextcord.ui.View):
    def __init__(self, description: str, global_avatar: str, guild_avatar: str):
        super().__init__()
        self.value = None
        self.description = description
        self.global_avatar = global_avatar
        self.guild_avatar = guild_avatar
    
    @nextcord.ui.button(label=f"Globale", style=nextcord.ButtonStyle.green, )
    async def set_global_avatar(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        embed = nextcord.Embed(description=f"{self.description}", color=config.get("embed-color"))
        embed.set_image(url=f"{self.global_avatar}")
        await interaction.message.edit(embed=embed)
        await interaction.response.defer()

    @nextcord.ui.button(label=f"Serveur", style=nextcord.ButtonStyle.green, )
    async def set_guild_avatar(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        embed = nextcord.Embed(description=f"{self.description}", color=config.get("embed-color"))
        embed.set_image(url=f"{self.guild_avatar}")
        await interaction.message.edit(embed=embed)
        await interaction.response.defer()


def _avatar(lang: str, member: nextcord.Member):
    # Note: nextcord.Member will be nextcord.User is the command is used in DMs,
    # so we need to check the type before accessing guild-specific attributes
    
    # member.avatar and member.default_avatar are Asset objects; convert to str
    global_asset = member.avatar or member.default_avatar
    global_avatar = str(global_asset)

    guild_asset = member.guild_avatar if isinstance(member, nextcord.Member) else None
    guild_avatar = str(guild_asset) if guild_asset else None 
    
    description = f"[{text('avatar_global', lang)}]({global_avatar})"
    if guild_avatar:
        description += f" • [{text('avatar_guild', lang)}]({guild_avatar})"
    
    embed = nextcord.Embed(description=f"{description}",color=config.get("embed-color"))
    # embed.set_image expects a URL string, not an Asset
    if guild_avatar:
        embed.set_image(url=guild_avatar)
    else:
        embed.set_image(url=global_avatar)
    
    return embed, global_avatar, guild_avatar, description

async def avatar_text(lang: str, message: nextcord.Message):
    member = await get_user(message)
    embed, global_avatar, guild_avatar, description = _avatar(lang, member)
    
    await message.reply(
        embed=embed,
        mention_author=False,
        view=AvatarView(description, global_avatar, guild_avatar) if guild_avatar else None
    )

async def avatar_slash(lang: str, interaction: nextcord.Interaction, member: nextcord.Member):
    embed, global_avatar, guild_avatar, description = _avatar(lang, member)
    
    await interaction.response.send_message(
        embed=embed,
        view=AvatarView(description, global_avatar, guild_avatar) if guild_avatar else nextcord.utils.MISSING
    )


info = {
    "avatar": {
        "category": "utilities",
        "aliases": ["pfp", "pp", "profilepic"],
        "hidden_aliases": ["profilepicture", "avtr", "photo", "pdp", "icon"],
        "available": ["slash_command", "text_command"],
        "visibility": "everyone",
        "user_permissions": [],
        "name": "avatar_name",
        "desc": "avatar_desc",
        "args": [
            {
                "name": "avatar_arg_name",
                "desc": "avatar_arg_desc"
            }
        ]
    }
}

cmd = CmdLocale(list(info.keys())[0], get_commands_locales(info))

class AvatarCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @check_ban()
    @slash_command(
        name=cmd.name,
        description=cmd.description,
        name_localizations=cmd.name_localizations,
        description_localizations=cmd.description_localizations
    )
    async def avatar_command(self, interaction: nextcord.Interaction,
        member: nextcord.Member = get_slash_option(cmd.arg(0)),
    ):
        await avatar_slash(get_lang(interaction), interaction, member)


def setup(bot: commands.Bot):
    bot.add_cog(AvatarCog(bot))

# Text command handler wrapper that adapts to message handler signature
async def _message_handler(bot, message: nextcord.Message, lang: str, prefix: str):
    await avatar_text(lang, message)
