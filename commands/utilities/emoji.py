import nextcord
from nextcord.ext import commands, application_checks
from nextcord.application_command import slash_command, message_command
from utils.logger import log
from utils.get_commands_locales import get_commands_locales
from utils.locale_helpers import CmdLocale, get_slash_option
from utils import config
from utils.settings.bot_ban import check_ban
from utils.languages import text
from utils.settings import prefix
from utils.settings.lang import get_lang

from utils.is_emoji import is_emoji
import utils.global_variables as gv
import json
from pathlib import Path
import random
import re
import requests
import time

TWEMOJI_INDEX_URL = "https://data.jsdelivr.com/v1/package/gh/jdecked/twemoji@17.0.2?structure=flat"
TWEMOJI_CACHE_PATH = Path(".cache/twemoji_unicode_emojis.json")
TWEMOJI_CACHE_TTL_SECONDS = 60 * 60 * 24 * 7


def _read_unicode_emoji_cache(allow_stale: bool = False) -> list[str] | None:
    if not TWEMOJI_CACHE_PATH.exists():
        return None

    try:
        with TWEMOJI_CACHE_PATH.open("r", encoding="utf-8") as cache_file:
            payload = json.load(cache_file)
    except (OSError, json.JSONDecodeError) as err:
        log.warning(f"Failed to read Twemoji cache: {err}")
        return None

    emojis = payload.get("emojis")
    fetched_at = payload.get("fetched_at", 0)
    if not isinstance(emojis, list):
        return None

    is_fresh = time.time() - fetched_at < TWEMOJI_CACHE_TTL_SECONDS
    if allow_stale or is_fresh:
        return emojis
    return None


def _write_unicode_emoji_cache(emojis: list[str]) -> None:
    try:
        TWEMOJI_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with TWEMOJI_CACHE_PATH.open("w", encoding="utf-8") as cache_file:
            json.dump({"fetched_at": int(time.time()), "emojis": emojis}, cache_file)
    except OSError as err:
        log.warning(f"Failed to write Twemoji cache: {err}")

def _get_all_unicode_emojis() -> list[str]:
    """Returns a list of all unicode emojis available in the twemoji API."""
    cached_emojis = _read_unicode_emoji_cache()
    if cached_emojis is not None:
        return cached_emojis

    try:
        response = requests.get(TWEMOJI_INDEX_URL, timeout=30)
        response.raise_for_status()
    except requests.RequestException as err:
        stale_cached_emojis = _read_unicode_emoji_cache(allow_stale=True)
        if stale_cached_emojis is not None:
            log.warning(f"Using stale Twemoji cache after fetch failure: {err}")
            return stale_cached_emojis
        raise

    emojis: list[str] = []
    for file_data in response.json().get("files", []):
        file_name = file_data.get("name", "")
        if not file_name.startswith("/assets/svg/") or not file_name.endswith(".svg"):
            continue

        emoji_name = file_name.removeprefix("/assets/svg/").removesuffix(".svg")
        emojis.append(emoji_name)
    _write_unicode_emoji_cache(emojis)
    return emojis

all_unicode_emojis: list[str] = _get_all_unicode_emojis()

client: nextcord.Client = gv.get("client")

def _emoji_embed(input: str, lang: str) -> nextcord.Embed:
    """Returns an embed with the emoji information.
    If the emoji is not found/is just text, find an emoji among the available emojis the bot has access to.
    If the emoji is unicode, use the unicode character as the emoji.
    """
    def _make_embed(emoji: nextcord.Emoji, input: str = "", not_found: bool = False, is_unicode: bool = False, unicode_id: str = "") -> nextcord.Embed:
        not_found_url: str = "https://discord.com/assets/3eb3ebe2d01299ec.svg"
        not_found_url_thumbnail: str = "https://cdn.discordapp.com/emojis/932254269183238155.webp?size=128"
        unicode_emoji_url: str = f"https://cdn.jsdelivr.net/gh/jdecked/twemoji@latest/assets/svg/{unicode_id}.svg" if is_unicode else emoji.url
        unicode_emoji_url_thumbnail: str = f"https://cdn.jsdelivr.net/gh/jdecked/twemoji@latest/assets/72x72/{unicode_id}.png" if is_unicode else not_found_url_thumbnail if not_found else emoji.url
        
        download_url: str = unicode_emoji_url if is_unicode else not_found_url if not_found else emoji.url
        thumbnail_url: str = unicode_emoji_url_thumbnail if is_unicode else not_found_url_thumbnail if not_found else emoji.url
        
        embed = nextcord.Embed(
            title=f"{emoji if emoji.id else input} - Emoji",
            description=f"```{text('emoji_name_', lang)}: {emoji.name}\n"
                           f"{text('emoji_id', lang)}: {emoji.id if not is_unicode else unicode_id}\n"  # noqa: E131
                           f"{text('emoji_animated', lang)}: {emoji.animated}\n"
                           f"{text('emoji_twitch', lang)}: {emoji.managed}\n"
                           f"{text('emoji_available', lang)}: {emoji.available}```\n"
                           f"[{text('emoji_download_url', lang)}]({download_url})",
            # TODO: Add provenance (user/application_id) (check for manage_emojis for both user in the guild + bot)
            color=config.get("embed-color")
        )
        embed.set_thumbnail(url=thumbnail_url)
        return embed
    
    def _get_unicode_emoji_id(emoji: str) -> str:
        def _unicode_id_candidates(value: str) -> list[str]:
            value = value.strip()
            exact = "-".join(f"{ord(c):x}" for c in value)
            no_vs16 = None if "\ufe0f" not in value else "-".join(f"{ord(c):x}" for c in value.replace("\ufe0f", ""))
            if no_vs16:
                return list(dict.fromkeys([exact, no_vs16]))
            return [exact]

        candidates = _unicode_id_candidates(emoji)
        # In case of multiple candidates, get the first one that matches a twemoji
        return str(next((c for c in candidates if c in all_unicode_emojis), None))
    
    def _get_emoji_id_regex(input: str) -> int:
        match = re.search(r'\d{17,21}', input)
        return int(match.group()) if match else 0
    
    def _get_similar_emoji(input: str) -> nextcord.Emoji | None:
        similar_emojis: list[nextcord.Emoji | None] = []
        for i in client.guilds:
            matching_emojis = nextcord.utils.get(i.emojis, name=input)
            if matching_emojis:
                similar_emojis.append(matching_emojis)
        return random.choice(similar_emojis) if similar_emojis else None
    
    # If the input is already an unicode emoji, return it directly
    input = input.replace('[FREE]', '🆓')  # weird discord behavior
    if is_emoji(input):
        return _make_embed(
            nextcord.Emoji(
                state=None,
                data={"name": input, "id": 0},
            ),
            input=input,
            is_unicode=True,
            unicode_id=_get_unicode_emoji_id(input),
        )
    
    # Process custom emojis
    emoji = client.get_emoji(_get_emoji_id_regex(input))
    if emoji is not None:
        return _make_embed(emoji)
    else:
        similar_emoji: nextcord.Emoji | None = _get_similar_emoji(input)
        if similar_emoji:
            return _make_embed(similar_emoji)
        else:
            # Create a fake emoji if no similar emoji is found
            not_found_emoji = nextcord.Emoji(
                state=None,
                data={
                    "name": input,
                    "id": 0,
                    "animated": False,
                    "managed": False,
                    "available": False,
                },
            )
            return _make_embed(not_found_emoji, input=input, not_found=True)
            # return nextcord.Embed(title="Error", description=f"Could not find emoji {input}")


async def emoji_text(lang: str, message: nextcord.Message):
    await message.reply(
        embed=_emoji_embed(message.content, lang),
        mention_author=False
    )

async def emoji_slash(lang: str, interaction: nextcord.Interaction, emoji: str):
    await interaction.response.send_message(
        embed=_emoji_embed(emoji, lang),
        ephemeral=False
    )


info = {
    "emoji": {
        "category": "utilities",
        "aliases": ["emote"],
        "hidden_aliases": ["e"],
        "available": ["slash_command", "text_command"],
        "visibility": "everyone",
        "user_permissions": [],
        "name": "emoji_name",
        "desc": "emoji_desc",
        "args": [
            {
                "name": "emoji_arg_name",
                "desc": "emoji_arg_desc"
            }
        ]
    }
}

cmd = CmdLocale(list(info.keys())[0], get_commands_locales(info))

class EmojiCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @check_ban()
    @slash_command(
        name=cmd.name,
        description=cmd.description,
        name_localizations=cmd.name_localizations,
        description_localizations=cmd.description_localizations
    )
    async def emoji_command(self, interaction: nextcord.Interaction,
        emoji: str = get_slash_option(cmd.arg(0))
    ):
        await emoji_slash(get_lang(interaction), interaction, emoji)


def setup(bot: commands.Bot):
    bot.add_cog(EmojiCog(bot))

# Text command handler wrapper that adapts to message handler signature
async def _message_handler(bot, message: nextcord.Message, lang: str, guild_prefix: str):
    await emoji_text(lang, message)
