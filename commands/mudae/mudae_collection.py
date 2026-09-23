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

from utils.sql.mudae import build_image_url, get_user_collection
from utils.mudae_media import GENDER_EMOJIS, format_rank, get_kakera_emoji, resolve_character_image
from utils.mudae_views import TimedDisableView

PAGE_SIZE = 10  # characters per page for $mm
COLLECTION_VIEW_TIMEOUT = 180  # 3 minutes to browse before the buttons stop responding


def _avatar_url(user: nextcord.abc.User) -> str:
    return str(user.avatar or user.default_avatar)


def _most_valuable(collection: list[dict]) -> dict | None:
    if not collection:
        return None
    return max(collection, key=lambda c: c["kakera_value"])


class MudaeListView(TimedDisableView):
    """$mm: paginated list of character names, PAGE_SIZE per page."""

    def __init__(self, lang: str, requester_id: int, display_name: str, collection: list[dict]):
        super().__init__(timeout=COLLECTION_VIEW_TIMEOUT)
        self.lang = lang
        self.requester_id = requester_id
        self.display_name = display_name
        self.pages = [
            collection[i:i + PAGE_SIZE] for i in range(0, len(collection), PAGE_SIZE)
        ] or [[]]
        self.page = 0

        most_valuable = _most_valuable(collection)
        image_path = most_valuable["images"][0] if most_valuable and most_valuable["images"] else None
        self.raw_thumbnail_url = build_image_url(image_path)
        # Resolved (possibly attachment://) thumbnail URL, filled in by the
        # caller once it's awaited resolve_character_image(). Embeds are
        # fully replaced on edit, so every build_embed() call must re-set it
        # or the thumbnail would disappear after the first page turn.
        self.resolved_thumbnail_url: str | None = None

        self._refresh_buttons()

    def _refresh_buttons(self):
        self.previous_button.disabled = self.page == 0
        self.next_button.disabled = self.page >= len(self.pages) - 1

    async def interaction_check(self, interaction: nextcord.Interaction) -> bool:
        if interaction.user.id != self.requester_id:
            await interaction.response.send_message(
                text('mudae_collection_not_for_you', self.lang), ephemeral=True
            )
            return False
        return True

    def build_embed(self) -> nextcord.Embed:
        names = "\n".join(character["name"] for character in self.pages[self.page])
        if not names:
            names = text('mudae_collection_empty', self.lang)

        embed = nextcord.Embed(description=names, color=config.get('embed-color'))
        embed.set_author(
            name=text('mudae_harem_title', self.lang).replace('%user%', self.display_name)
        )
        footer_text = text('mudae_collection_page_footer', self.lang) \
            .replace('%current%', str(self.page + 1)) \
            .replace('%total%', str(len(self.pages)))
        embed.set_footer(text=footer_text)
        if self.resolved_thumbnail_url:
            embed.set_thumbnail(url=self.resolved_thumbnail_url)
        return embed

    @nextcord.ui.button(label="◀", style=nextcord.ButtonStyle.secondary)
    async def previous_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        self.page = max(0, self.page - 1)
        self._refresh_buttons()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @nextcord.ui.button(label="▶", style=nextcord.ButtonStyle.secondary)
    async def next_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        self.page = min(len(self.pages) - 1, self.page + 1)
        self._refresh_buttons()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)


class MudaeCardView(TimedDisableView):
    """$mmi: one character per page, with its big image."""

    def __init__(self, lang: str, requester_id: int, display_name: str, collection: list[dict]):
        super().__init__(timeout=COLLECTION_VIEW_TIMEOUT)
        self.lang = lang
        self.requester_id = requester_id
        self.display_name = display_name
        self.collection = collection
        self.page = 0
        self._refresh_buttons()

    def _refresh_buttons(self):
        self.previous_button.disabled = self.page == 0
        self.next_button.disabled = self.page >= len(self.collection) - 1

    async def interaction_check(self, interaction: nextcord.Interaction) -> bool:
        if interaction.user.id != self.requester_id:
            await interaction.response.send_message(
                text('mudae_collection_not_for_you', self.lang), ephemeral=True
            )
            return False
        return True

    async def build_page(self) -> tuple[nextcord.Embed, nextcord.File | None]:
        character = self.collection[self.page]
        gender_emoji = GENDER_EMOJIS.get(character["gender"], GENDER_EMOJIS[0])
        series_type = character["series_type"] or text('mudae_unknown_type', self.lang)

        description_lines = [
            f"{character['series_name'] or text('mudae_unknown_series', self.lang)} {gender_emoji}",
            f"{series_type} · {character['kakera_value']} {get_kakera_emoji()}",
            f"{text('mudae_claims_label', self.lang)}: {format_rank(character['rank'], self.lang)}",
            f"{text('mudae_likes_label', self.lang)}: {format_rank(character['like_rank'], self.lang)}",
        ]

        embed = nextcord.Embed(
            title=character["name"],
            description="\n".join(description_lines),
            color=config.get('embed-color'),
        )
        footer_text = text('mudae_card_footer', self.lang) \
            .replace('%user%', self.display_name) \
            .replace('%current%', str(self.page + 1)) \
            .replace('%total%', str(len(self.collection)))
        embed.set_footer(text=footer_text)

        image_path = character["images"][0] if character["images"] else None
        image_url, image_file = await resolve_character_image(build_image_url(image_path))
        if image_url:
            embed.set_image(url=image_url)

        return embed, image_file

    @nextcord.ui.button(label="◀", style=nextcord.ButtonStyle.secondary)
    async def previous_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        self.page = max(0, self.page - 1)
        self._refresh_buttons()
        embed, image_file = await self.build_page()
        kwargs = {"embed": embed, "view": self}
        if image_file:
            kwargs["file"] = image_file
        await interaction.response.edit_message(**kwargs)

    @nextcord.ui.button(label="▶", style=nextcord.ButtonStyle.secondary)
    async def next_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        self.page = min(len(self.collection) - 1, self.page + 1)
        self._refresh_buttons()
        embed, image_file = await self.build_page()
        kwargs = {"embed": embed, "view": self}
        if image_file:
            kwargs["file"] = image_file
        await interaction.response.edit_message(**kwargs)


async def _send_list(lang: str, user: nextcord.abc.User, guild_id: int, send) -> nextcord.ui.View:
    collection = get_user_collection(user.id, guild_id)
    view = MudaeListView(lang, user.id, user.display_name, collection)

    image_url, image_file = await resolve_character_image(view.raw_thumbnail_url)
    view.resolved_thumbnail_url = image_url

    embed = view.build_embed()
    embed.set_author(
        name=text('mudae_harem_title', lang).replace('%user%', user.display_name),
        icon_url=_avatar_url(user)
    )

    kwargs = {"embed": embed, "view": view}
    if image_file:
        kwargs["file"] = image_file
    sent = await send(**kwargs)
    if sent is not None:
        view.bind_message(sent)
    return view


async def _send_cards(lang: str, user: nextcord.abc.User, guild_id: int, send) -> nextcord.ui.View | None:
    collection = get_user_collection(user.id, guild_id)

    if not collection:
        await send(content=text('mudae_collection_empty', lang))
        return None

    view = MudaeCardView(lang, user.id, user.display_name, collection)
    embed, image_file = await view.build_page()

    kwargs = {"embed": embed, "view": view}
    if image_file:
        kwargs["file"] = image_file
    sent = await send(**kwargs)
    if sent is not None:
        view.bind_message(sent)
    return view


async def mudae_list_text(lang: str, message: nextcord.Message):
    async def send(**kwargs):
        return await message.reply(mention_author=False, **kwargs)

    await _send_list(lang, message.author, message.guild.id, send)


async def mudae_list_slash(lang: str, interaction: nextcord.Interaction):
    async def send(**kwargs):
        await interaction.response.send_message(**kwargs)
        return None

    view = await _send_list(lang, interaction.user, interaction.guild_id, send)
    view.bind_interaction(interaction)


async def mudae_cards_text(lang: str, message: nextcord.Message):
    async def send(**kwargs):
        return await message.reply(mention_author=False, **kwargs)

    await _send_cards(lang, message.author, message.guild.id, send)


async def mudae_cards_slash(lang: str, interaction: nextcord.Interaction):
    async def send(**kwargs):
        await interaction.response.send_message(**kwargs)
        return None

    view = await _send_cards(lang, interaction.user, interaction.guild_id, send)
    if view is not None:
        view.bind_interaction(interaction)


info = {
    "mm": {
        "category": "mudae",
        "aliases": ["harem"],
        "hidden_aliases": [],
        "available": ["slash_command", "text_command"],
        "dm_available": False,
        "visibility": "everyone",
        "user_permissions": [],
        "name": "mm_name",
        "desc": "mm_desc",
        "args": []
    },
    "mmi": {
        "category": "mudae",
        "aliases": ["haremimage", "harem_image"],
        "hidden_aliases": [],
        "available": ["slash_command", "text_command"],
        "dm_available": False,
        "visibility": "everyone",
        "user_permissions": [],
        "name": "mmi_name",
        "desc": "mmi_desc",
        "args": []
    },
}

locales = get_commands_locales(info)
cmd_mm = CmdLocale("mm", locales)
cmd_mmi = CmdLocale("mmi", locales)


class MudaeCollectionCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @check_ban()
    @checks.guild_only()
    @slash_command(
        name=cmd_mm.name,
        description=cmd_mm.description,
        name_localizations=cmd_mm.name_localizations,
        description_localizations=cmd_mm.description_localizations,
    )
    async def mm_command(self, interaction: nextcord.Interaction):
        await mudae_list_slash(get_lang(interaction), interaction)

    @check_ban()
    @checks.guild_only()
    @slash_command(
        name=cmd_mmi.name,
        description=cmd_mmi.description,
        name_localizations=cmd_mmi.name_localizations,
        description_localizations=cmd_mmi.description_localizations,
    )
    async def mmi_command(self, interaction: nextcord.Interaction):
        await mudae_cards_slash(get_lang(interaction), interaction)


def setup(bot: commands.Bot):
    bot.add_cog(MudaeCollectionCog(bot))


@checks.guild_only()
async def _message_handler_mm(bot, message: nextcord.Message, lang: str, prefix_str: str):
    await mudae_list_text(lang, message)


@checks.guild_only()
async def _message_handler_mmi(bot, message: nextcord.Message, lang: str, prefix_str: str):
    await mudae_cards_text(lang, message)


_message_handlers = {
    "mm": _message_handler_mm,
    "mmi": _message_handler_mmi,
}
