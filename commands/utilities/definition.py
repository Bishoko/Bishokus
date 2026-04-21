import nextcord
from nextcord.ext import commands
from nextcord.application_command import slash_command
from utils.get_commands_locales import get_commands_locales
from utils.locale_helpers import CmdLocale, get_slash_option
from utils import config
from utils.settings.bot_ban import check_ban
from utils.languages import text
from utils.settings.lang import get_lang

import aiohttp
import re
from urllib.parse import quote
from larousse_api import larousse

DICTIONARY_BASE_URL = "https://freedictionaryapi.com/api/v1/entries"
WIKTIONARY_ICON_URL = "https://upload.wikimedia.org/wikipedia/commons/b/be/Logo_15_in_wiktionary_vote_round_1.png"
LAROUSSE_ICON_URL = "https://media.discordapp.net/attachments/939294227152662589/995836683746545804/logo_larousse.png"

class DefinitionView(nextcord.ui.View):
    def __init__(self, ui_lang: str, word: str, selected_lookup_lang: str):
        super().__init__(timeout=None)
        self.ui_lang = ui_lang
        self.word = word
        self.selected_lookup_lang = selected_lookup_lang
        self.set_french_definition.label = text("definition_lang_french", ui_lang)
        self.set_english_definition.label = text("definition_lang_english", ui_lang)
        self._sync_button_styles()

    def _sync_button_styles(self):
        is_french_selected = self.selected_lookup_lang == "fr"
        self.set_french_definition.style = (
            nextcord.ButtonStyle.green if is_french_selected else nextcord.ButtonStyle.gray
        )
        self.set_english_definition.style = (
            nextcord.ButtonStyle.green if not is_french_selected else nextcord.ButtonStyle.gray
        )

    async def _update_definition(self, interaction: nextcord.Interaction, lookup_lang: str):
        await interaction.response.defer()
        self.selected_lookup_lang = lookup_lang
        self._sync_button_styles()
        embed = await _definition_embed(self.ui_lang, self.word, lookup_lang)
        await interaction.message.edit(embed=embed, view=self)

    @nextcord.ui.button(label="Français", style=nextcord.ButtonStyle.green)
    async def set_french_definition(
        self,
        button: nextcord.ui.Button,
        interaction: nextcord.Interaction,
    ):
        await self._update_definition(interaction, "fr")

    @nextcord.ui.button(label="English", style=nextcord.ButtonStyle.gray)
    async def set_english_definition(
        self,
        button: nextcord.ui.Button,
        interaction: nextcord.Interaction,
    ):
        await self._update_definition(interaction, "en")


def _normalize_word(raw_word: str) -> str:
    """Normalize spacing and remove leading command leftovers from user input."""
    cleaned = raw_word.strip()
    # message.content already excludes the command, but we keep this to avoid malformed manual inputs.
    cleaned = re.sub(r"^[/!]+", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def _dictionary_lang_code(lang: str) -> str:
    return "fr" if lang.startswith("fr") else "en"


def _get_lookup_language_name(lookup_lang: str, ui_lang: str) -> str:
    if lookup_lang == "fr":
        return text("definition_lang_french", ui_lang)
    return text("definition_lang_english", ui_lang)


async def _fetch_definition_payload(word: str, lang_code: str) -> dict:
    encoded_word = quote(word)
    url = f"{DICTIONARY_BASE_URL}/{lang_code}/{encoded_word}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status != 200:
                    return {}
                payload = await response.json()
                if isinstance(payload, dict):
                    return payload
                return {}
    except (aiohttp.ClientError, Exception):
        return {}


def _fetch_larousse_definitions(word: str) -> list[str]:
    try:
        return larousse.get_definitions(word) or []
    except Exception:
        return []

def _entry_language_code(entry: dict) -> str:
    language = entry.get("language")
    if not isinstance(language, dict):
        return ""
    return str(language.get("code", "")).strip().lower()


def _format_entry(entry: dict, entry_index: int) -> str:
    part_of_speech = str(entry.get("partOfSpeech", "")).strip() or "unknown"

    lines = [f"**{entry_index}. {part_of_speech}**"]

    senses = entry.get("senses", [])
    for idx, sense in enumerate(senses, start=1):
        if not isinstance(sense, dict):
            continue

        definition_value = str(sense.get("definition", "")).strip()
        if not definition_value:
            continue

        tags = [tag.strip() for tag in sense.get("tags", []) if isinstance(tag, str) and tag.strip()]
        tag_prefix = f"*[{', '.join(tags)}]* " if tags else ""
        lines.append(f"{idx}. {tag_prefix}{definition_value}")

        examples = sense.get("examples", [])
        if examples:
            first_example = str(examples[0]).strip()
            if first_example:
                lines.append(f"> {first_example}")

    return "\n".join(lines)


def _split_entries_by_language(entries: list, lookup_lang: str) -> tuple[list[dict], list[dict]]:
    if not isinstance(entries, list):
        return [], []

    primary: list[dict] = []
    secondary: list[dict] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if _entry_language_code(entry) == lookup_lang:
            primary.append(entry)
        else:
            secondary.append(entry)

    return primary, secondary


def _best_source_url(lookup_lang: str, word: str) -> str:
    if lookup_lang == "fr":
        return f"https://www.larousse.fr/dictionnaires/francais/{quote(word)}"
    return f"https://en.wiktionary.org/wiki/{quote(word)}"


def _compose_description(primary: list[dict], secondary: list[dict], ui_lang: str) -> str:
    if not primary and not secondary:
        return ""

    blocks: list[str] = []
    for idx, entry in enumerate(primary, start=1):
        blocks.append(_format_entry(entry, idx))

    if secondary:
        label = "Autres langues" if ui_lang.startswith("fr") else "Other languages"
        blocks.append(f"**{label}**")
        for idx, entry in enumerate(secondary[:2], start=1):
            blocks.append(_format_entry(entry, idx))

    description = "\n\n".join(blocks)
    if len(description) > 3900:
        return description[:3897] + "..."
    return description


def _extract_definition_text(entries: list, lookup_lang: str, ui_lang: str) -> str:
    primary, secondary = _split_entries_by_language(entries, lookup_lang)
    return _compose_description(primary, secondary, ui_lang)


def _format_larousse_definitions(definitions: list[str]) -> str:
    if not definitions:
        return ""
    description = "\n".join(definitions)
    if len(description) > 3900:
        return description[:3897] + "..."
    return description


def _build_not_found_embed(word: str, lang: str) -> nextcord.Embed:
    embed = nextcord.Embed(
        title=f"\u201c{word}\u201d",
        description=text("definition_not_found", lang),
        color=nextcord.Colour(config.get("embed-color")),
    )
    embed.set_author(
        name=text("definition_embed_author", lang),
        icon_url=LAROUSSE_ICON_URL,
    )
    return embed


def _build_definition_embed(word: str, definition: str, lang: str, lookup_lang: str, source_url: str) -> nextcord.Embed:
    embed = nextcord.Embed(
        title=f"\u201c{word}\u201d",
        description=definition,
        color=nextcord.Colour(config.get("embed-color")),
    )
    embed.set_author(
        name=text("definition_embed_author", lang),
        icon_url=LAROUSSE_ICON_URL,
    )
    embed.add_field(
        name=text("definition_language_label", lang),
        value=_get_lookup_language_name(lookup_lang, lang),
        inline=True,
    )
    embed.add_field(
        name=text("definition_source_label", lang),
        value=f"[{'Larousse' if lookup_lang == 'fr' else 'Wiktionary'}]({source_url})",
        inline=True,
    )
    return embed


async def _definition_embed(lang: str, word: str, lookup_lang: str) -> nextcord.Embed:
    if lookup_lang == "fr":
        definitions = _fetch_larousse_definitions(word)
        definition = _format_larousse_definitions(definitions)
    else:
        payload = await _fetch_definition_payload(word, lookup_lang)
        definition = _extract_definition_text(payload.get("entries", []), lookup_lang, lang)

    if not definition:
        return _build_not_found_embed(word, lang)

    source_url = _best_source_url(lookup_lang, word)
    return _build_definition_embed(word, definition, lang, lookup_lang, source_url)


async def _definition(lang: str, raw_word: str) -> tuple[nextcord.Embed | None, str | None, str | None]:
    word = _normalize_word(raw_word)
    if not word:
        return None, text("definition_empty_error", lang), None

    lookup_lang = _dictionary_lang_code(lang)
    embed = await _definition_embed(lang, word, lookup_lang)
    return embed, None, word


async def definition_text(lang: str, message: nextcord.Message):
    async with message.channel.typing():
        embed, error, word = await _definition(lang, message.content)

    if error:
        await message.reply(error, mention_author=False)
        return

    await message.reply(
        embed=embed,
        mention_author=False,
        view=DefinitionView(lang, word, _dictionary_lang_code(lang)),
    )


async def definition_slash(lang: str, interaction: nextcord.Interaction, word: str):
    await interaction.response.defer()
    embed, error, normalized_word = await _definition(lang, word)

    if error:
        await interaction.followup.send(error, ephemeral=True)
        return

    await interaction.followup.send(
        embed=embed,
        view=DefinitionView(lang, normalized_word, _dictionary_lang_code(lang)),
    )


info = {
    "definition": {
        "category": "utilities",
        "aliases": [],
        "hidden_aliases": ["dictionnaire", "dictionaire", "dico", "larousse", "larouse",
                           "definnition", "def", "dictionary", "define",
                           "meaning", "meaningof", "worddef", "worddefinition",
                           "lexicon"],
        "available": ["slash_command", "text_command"],
        "visibility": "everyone",
        "user_permissions": [],
        "name": "definition_name",
        "desc": "definition_desc",
        "args": [
            {
                "name": "definition_word_arg_name",
                "desc": "definition_word_arg_desc"
            }
        ]
    }
}

cmd = CmdLocale(list(info.keys())[0], get_commands_locales(info))

class DefinitionCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @check_ban()
    @slash_command(
        name=cmd.name,
        description=cmd.description,
        name_localizations=cmd.name_localizations,
        description_localizations=cmd.description_localizations
    )
    async def definition_command(self, interaction: nextcord.Interaction,
        word: str = get_slash_option(cmd.arg(0))
    ):
        await definition_slash(get_lang(interaction), interaction, word)


def setup(bot: commands.Bot):
    bot.add_cog(DefinitionCog(bot))

# Text command handler wrapper that adapts to message handler signature
async def _message_handler(bot, message: nextcord.Message, lang: str, guild_prefix: str):
    await definition_text(lang, message)
