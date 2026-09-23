import io
import os
from urllib.parse import urlparse

import aiohttp
import nextcord

import utils.global_variables as gv
from utils.languages import text
from utils.logger import log
from utils.config import config

LOCAL_MEDIA_HOSTS = {"localhost", "127.0.0.1"}

GENDER_EMOJIS = {
    0: "❔",
    1: "♂️",
    2: "♀️",
    3: "⚧️",
}


def format_rank(rank: int | None, lang: str) -> str:
    return f"#{rank:,}" if rank else text('mudae_unranked', lang)


def _find_kakera_emoji():
    bot = gv.get('bot') or gv.get('client')
    if bot is not None:
        return nextcord.utils.get(bot.emojis, name="kakera")
    return None


def get_kakera_emoji() -> str:
    return str(_find_kakera_emoji() or config.get('default-mudae-emoji'))


def get_kakera_button_emoji():
    """Returns something usable as a nextcord.ui.Button's `emoji=` kwarg
    (an Emoji object or a unicode string) rather than the mention string
    get_kakera_emoji() returns - buttons render emoji, not markdown."""
    return _find_kakera_emoji() or config.get('default-mudae-emoji')


async def resolve_character_image(image_url: str | None) -> tuple[str | None, nextcord.File | None]:
    """Discord's embed proxy can't reach localhost/127.0.0.1 (used during
    local dev), so those need to be downloaded and re-uploaded as an
    attachment instead of linked directly."""
    if not image_url:
        return None, None

    if urlparse(image_url).hostname not in LOCAL_MEDIA_HOSTS:
        return image_url, None

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status != 200:
                    return None, None
                data = await response.read()
    except aiohttp.ClientError as e:
        log.warning(f"Failed to fetch local mudae character image {image_url}: {e}")
        return None, None

    filename = os.path.basename(urlparse(image_url).path) or "character.png"
    return f"attachment://{filename}", nextcord.File(io.BytesIO(data), filename=filename)
