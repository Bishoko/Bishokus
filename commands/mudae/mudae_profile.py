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

from utils.sql.mudae import build_image_url, get_user_profile
from utils.mudae_media import GENDER_EMOJIS, get_kakera_emoji, resolve_character_image

GENDER_DISPLAY_ORDER = [2, 1, 3, 0]


def _format_gender_breakdown(gender_counts: dict, total: int) -> str:
    parts = []
    for gender in GENDER_DISPLAY_ORDER:
        count = gender_counts.get(gender, 0)
        if not count:
            continue
        percent = round(count / total * 100)
        parts.append(f"{percent}% {GENDER_EMOJIS[gender]}")
    return " ".join(parts)


def _build_profile_embed(lang: str, display_name: str, avatar_url: str, profile: dict) -> tuple[nextcord.Embed, str | None]:
    collection_size = profile["collection_size"]

    collection_line = f"{text('mudae_profile_collection_label', lang)}: {collection_size}"
    if collection_size:
        breakdown = _format_gender_breakdown(profile["gender_counts"], collection_size)
        if breakdown:
            collection_line += f" ({breakdown})"

    description = "\n\n".join([
        collection_line,
        f"{text('mudae_profile_kakera_label', lang)}\n{profile['kakera']:,} {get_kakera_emoji()}",
    ])

    embed = nextcord.Embed(
        description=description,
        color=config.get('embed-color'),
    )
    embed.set_author(name=display_name, icon_url=avatar_url)

    most_valuable = profile["most_valuable"]
    image_path = most_valuable["images"][0] if most_valuable and most_valuable["images"] else None

    return embed, build_image_url(image_path)


async def _send_profile(lang: str, display_name: str, avatar_url: str, user_id: int, guild_id: int, send) -> None:
    profile = get_user_profile(user_id, guild_id)
    embed, raw_image_url = _build_profile_embed(lang, display_name, avatar_url, profile)

    image_url, image_file = await resolve_character_image(raw_image_url)
    if image_url:
        embed.set_thumbnail(url=image_url)

    kwargs = {"embed": embed}
    if image_file:
        kwargs["file"] = image_file
    await send(**kwargs)


async def mudae_profile_text(lang: str, message: nextcord.Message):
    avatar_url = str(message.author.avatar or message.author.default_avatar)

    async def send(**kwargs):
        await message.reply(mention_author=False, **kwargs)

    await _send_profile(lang, message.author.display_name, avatar_url, message.author.id, message.guild.id, send)


async def mudae_profile_slash(lang: str, interaction: nextcord.Interaction):
    avatar_url = str(interaction.user.avatar or interaction.user.default_avatar)

    async def send(**kwargs):
        await interaction.response.send_message(**kwargs)

    await _send_profile(lang, interaction.user.display_name, avatar_url, interaction.user.id, interaction.guild_id, send)


info = {
    "profile": {
        "category": "mudae",
        "aliases": [],
        "hidden_aliases": [],
        "available": ["slash_command", "text_command"],
        "dm_available": False,
        "visibility": "everyone",
        "user_permissions": [],
        "name": "profile_name",
        "desc": "profile_desc",
        "args": []
    },
}

cmd = CmdLocale(list(info.keys())[0], get_commands_locales(info))


class MudaeProfileCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @check_ban()
    @checks.guild_only()
    @slash_command(
        name=cmd.name,
        description=cmd.description,
        name_localizations=cmd.name_localizations,
        description_localizations=cmd.description_localizations,
    )
    async def profile_command(self, interaction: nextcord.Interaction):
        await mudae_profile_slash(get_lang(interaction), interaction)


def setup(bot: commands.Bot):
    bot.add_cog(MudaeProfileCog(bot))


# Text command handler wrapper that adapts to message handler signature
@checks.guild_only()
async def _message_handler(bot, message: nextcord.Message, lang: str, prefix_str: str):
    await mudae_profile_text(lang, message)
