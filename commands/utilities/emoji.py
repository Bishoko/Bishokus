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
import random
import re


client: nextcord.Client = gv.get("client")

def _emoji_embed(input: str, lang: str) -> nextcord.Embed:
    """Returns an embed with the emoji information.
    If the emoji is not found/is just text, find an emoji among the available emojis the bot has access to.
    If the emoji is unicode, use the unicode character as the emoji.
    """
    # TODO: add support for emoji combinations. e.g. !emoji 👁‍🗨
    def _make_embed(emoji: nextcord.Emoji, input: str = "", not_found: bool = False, is_unicode: bool = False, unicode_id: str = "") -> nextcord.Embed:
        not_found_url: str = "https://discord.com/assets/3eb3ebe2d01299ec.svg"
        not_found_url_thumbnail: str = "https://cdn.discordapp.com/emojis/932254269183238155.webp?size=128"
        unicode_emoji_url: str = f"https://cdn.jsdelivr.net/gh/jdecked/twemoji@latest/assets/svg/{unicode_id}.svg" if is_unicode else emoji.url
        unicode_emoji_url_thumbnail: str = f"https://cdn.jsdelivr.net/gh/jdecked/twemoji@latest/assets/72x72/{unicode_id}.png" if is_unicode else not_found_url_thumbnail if not_found else emoji.url
        
        download_url: str = unicode_emoji_url if is_unicode else not_found_url if not_found else emoji.url
        thumbnail_url: str = unicode_emoji_url_thumbnail if is_unicode else not_found_url_thumbnail if not_found else emoji.url
        
        embed = nextcord.Embed(
            title=f"{emoji if emoji.id else input} - Emoji",
            description=f"```{text('emoji_name', lang)}: {emoji.name}\n"
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
        log.debug(emoji)
        # Remove fe0f (variation selector) from the emoji
        emoji = emoji.replace('\ufe0f', '').strip()
        log.debug(emoji)
        return "-".join([f"{ord(c):x}" for c in emoji])
    
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
