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


def _trim_field_value(value: str, limit: int = 1024) -> str:
    if len(value) <= limit:
        return value
    return value[:limit - 3] + "..."


def _build_roles_value(guild: nextcord.Guild, lang: str) -> str:
    roles = [role for role in guild.roles if role.name != "@everyone"]
    if not roles:
        return text("serverinfo_no_roles", lang)

    displayed_roles = list(reversed(roles))[:30]
    value = ", ".join(role.mention for role in displayed_roles)

    if len(roles) > len(displayed_roles):
        value += " " + text("serverinfo_and_more", lang)

    return _trim_field_value(value)


def _build_emojis_value(guild: nextcord.Guild, lang: str) -> str:
    available_emojis = [emoji for emoji in guild.emojis if emoji.available]
    if not available_emojis:
        return text("serverinfo_no_emojis", lang)

    displayed_emojis = list(reversed(available_emojis))[:30]
    value = " ".join(str(emoji) for emoji in displayed_emojis)

    if len(available_emojis) > len(displayed_emojis):
        value += " " + text("serverinfo_and_more", lang)

    return _trim_field_value(value)


def _format_boosts(guild: nextcord.Guild, lang: str) -> str:
    boost_count = guild.premium_subscription_count or 0
    boost_level = guild.premium_tier

    if boost_count == 0:
        return text("serverinfo_boosts_none", lang).replace("%boost_level%", str(boost_level))
    if boost_count == 1:
        return text("serverinfo_boosts_one", lang).replace("%boost_level%", str(boost_level))

    return (
        text("serverinfo_boosts_many", lang)
        .replace("%boost_count%", str(boost_count))
        .replace("%boost_level%", str(boost_level))
    )


def _serverinfo(lang: str, guild: nextcord.Guild) -> nextcord.Embed:
    total_members = guild.member_count or 0
    human_members = len([member for member in guild.members if not member.bot])
    bot_members = total_members - human_members

    text_channels = len(guild.text_channels)
    voice_channels = len(guild.voice_channels)
    threads = len(guild.threads)
    categories = len(guild.categories)
    total_channels = text_channels + voice_channels

    description = guild.description or text("serverinfo_no_description", lang)
    owner_mention = f"<@{guild.owner_id}>"

    icon_url = str(guild.icon.url) if guild.icon else None
    banner_url = str(guild.banner.url) if guild.banner else None

    embed = nextcord.Embed(
        title=text("serverinfo_embed_title", lang).replace("%guild_name%", guild.name),
        description=(
            text("serverinfo_channels_summary", lang)
            .replace("%total_channels%", str(total_channels))
            .replace("%text_channels%", str(text_channels))
            .replace("%voice_channels%", str(voice_channels))
            .replace("%threads%", str(threads))
            .replace("%categories%", str(categories))
        ),
        color=config.get("embed-color")
    )

    embed.add_field(name=text("serverinfo_field_description", lang), value=description, inline=False)
    embed.add_field(name=text("serverinfo_field_members", lang), value=str(total_members), inline=True)
    embed.add_field(name=text("serverinfo_field_humans", lang), value=str(human_members), inline=True)
    embed.add_field(name=text("serverinfo_field_bots", lang), value=str(bot_members), inline=True)
    embed.add_field(name=text("serverinfo_field_boosts", lang), value=_format_boosts(guild, lang), inline=True)
    embed.add_field(name=text("serverinfo_field_owner", lang), value=owner_mention, inline=True)

    embed.add_field(
        name=text("serverinfo_field_roles", lang).replace("%count%", str(max(len(guild.roles) - 1, 0))),
        value=_build_roles_value(guild, lang),
        inline=False,
    )
    embed.add_field(
        name=text("serverinfo_field_emojis", lang).replace("%count%", str(len(guild.emojis))),
        value=_build_emojis_value(guild, lang),
        inline=False,
    )

    if banner_url:
        embed.set_image(url=banner_url)

    if icon_url:
        embed.set_thumbnail(url=icon_url)

    embed.set_footer(text=text("serverinfo_footer", lang).replace("%guild_id%", str(guild.id)))

    return embed


async def serverinfo_text(lang: str, message: nextcord.Message):
    await message.reply(
        embed=_serverinfo(lang, message.guild),
        mention_author=False
    )

async def serverinfo_slash(lang: str, interaction: nextcord.Interaction):
    await interaction.response.send_message(
        embed=_serverinfo(lang, interaction.guild),
        ephemeral=False
    )


info = {
    "serverinfo": {
        "category": "utilities",
        "aliases": ["server", "serv"],
        "hidden_aliases": ["server_info", "servinfo", "si", "guildinfo", "guild"],
        "available": ["slash_command", "text_command"],
        "visibility": "everyone",
        "user_permissions": [],
        "name": "serverinfo_name",
        "desc": "serverinfo_desc",
        "args": []
    }
}

cmd = CmdLocale(list(info.keys())[0], get_commands_locales(info))

class ServerInfoCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @check_ban()
    @checks.guild_only()
    @slash_command(
        name=cmd.name,
        description=cmd.description,
        name_localizations=cmd.name_localizations,
        description_localizations=cmd.description_localizations
    )
    async def serverinfo_command(self, interaction: nextcord.Interaction):
        await serverinfo_slash(get_lang(interaction), interaction)


def setup(bot: commands.Bot):
    bot.add_cog(ServerInfoCog(bot))

# Text command handler wrapper that adapts to message handler signature
@checks.guild_only()
async def _message_handler(bot, message: nextcord.Message, lang: str, guild_prefix: str):
    await serverinfo_text(lang, message)
