import nextcord
from nextcord.ext import commands
from nextcord.application_command import slash_command
from utils.get_commands_locales import get_commands_locales
from utils.locale_helpers import CmdLocale, get_slash_option
from utils import config, checks
from utils.settings.bot_ban import check_ban
from utils.languages import text
from utils.settings.lang import get_lang

from utils.sql.mudae import (
    find_character,
    find_liked_character,
    find_liked_series,
    find_series,
    get_user_likes,
    like_character,
    like_series,
    search_characters,
    search_liked_characters,
    search_liked_series,
    search_series,
    unlike_character,
    unlike_series,
)
from utils.mudae_views import TimedDisableView

LIKELIST_PAGE_SIZE = 10
LIKELIST_VIEW_TIMEOUT = 180  # 3 minutes to browse before the buttons stop responding
SERIES_MARKER = "📺"

# Per command: how to look the target up, how to apply the change, the lang key
# prefix, and which lang key reports that the change had nothing to do. Like
# lookups search the whole catalog; unlike lookups only search the user's own likes.
ACTIONS = {
    "like": {
        "find": lambda user_id, query, guild_id, nsfw: find_character(query, guild_id, nsfw),
        "apply": like_character, "key": "mudae_like", "noop": "already_error",
    },
    "likem": {
        "find": lambda user_id, query, guild_id, nsfw: find_series(query, guild_id, nsfw),
        "apply": like_series, "key": "mudae_likem", "noop": "already_error",
    },
    "unlike": {
        "find": find_liked_character,
        "apply": unlike_character, "key": "mudae_unlike", "noop": "not_liked_error",
    },
    "unlikem": {
        "find": find_liked_series,
        "apply": unlike_series, "key": "mudae_unlikem", "noop": "not_liked_error",
    },
}


def _channel_allows_nsfw(channel) -> bool:
    is_nsfw = getattr(channel, "is_nsfw", None)
    if callable(is_nsfw):
        return is_nsfw()
    return False


def _avatar_url(user: nextcord.abc.User) -> str:
    return str(user.avatar or user.default_avatar)


def _format_candidate(candidate: dict) -> str:
    if candidate["detail"]:
        return f"- **{candidate['name']}** ({candidate['detail']})"
    return f"- **{candidate['name']}**"


def _autocomplete_options(results: list[dict]) -> dict:
    options = {}
    for result in results:
        label = result["name"] or result["uuid"]
        if result["detail"]:
            label = f"{label} ({result['detail']})"
        label = label[:100]
        if label in options:
            label = f"{label[:90]} #{result['uuid'][:8]}"
        options[label] = result["uuid"]
    return options


async def _apply_like(
    lang: str, action: str, user: nextcord.abc.User, query: str, guild_id: int, allow_nsfw: bool, send
):
    action_config = ACTIONS[action]
    key = action_config["key"]

    match, candidates = action_config["find"](user.id, query, guild_id, allow_nsfw)
    if match is None:
        if candidates:
            suggestions = "\n".join(_format_candidate(candidate) for candidate in candidates)
            error = text(f'{key}_ambiguous_error', lang) \
                .replace('%query%', query) \
                .replace('%suggestions%', suggestions)
        else:
            error = text(f'{key}_not_found_error', lang).replace('%query%', query)
        await send(error, ephemeral=True)
        return

    if not action_config["apply"](user.id, match["uuid"]):
        noop_message = text(f'{key}_{action_config["noop"]}', lang).replace('%name%', match["name"])
        await send(noop_message, ephemeral=True)
        return

    success = text(f'{key}_success', lang) \
        .replace('%user%', user.display_name) \
        .replace('%name%', match["name"]) \
        .replace('%serie%', match["detail"] or text('mudae_unknown_series', lang))
    await send(success)


class MudaeLikeListView(TimedDisableView):
    """Paginated list of the user's liked characters, followed by liked series."""

    def __init__(self, lang: str, requester_id: int, display_name: str, avatar_url: str, likes: dict):
        super().__init__(timeout=LIKELIST_VIEW_TIMEOUT)
        self.lang = lang
        self.requester_id = requester_id
        self.display_name = display_name
        self.avatar_url = avatar_url
        self.character_count = len(likes["characters"])
        self.series_count = len(likes["series"])

        entries = [character["name"] for character in likes["characters"]]
        entries += [f"{SERIES_MARKER} {series['name']}" for series in likes["series"]]
        self.pages = [
            entries[i:i + LIKELIST_PAGE_SIZE] for i in range(0, len(entries), LIKELIST_PAGE_SIZE)
        ] or [[]]
        self.page = 0
        self._refresh_buttons()

    def _refresh_buttons(self):
        self.previous_button.disabled = self.page == 0
        self.next_button.disabled = self.page >= len(self.pages) - 1

    async def interaction_check(self, interaction: nextcord.Interaction) -> bool:
        if interaction.user.id != self.requester_id:
            await interaction.response.send_message(
                text('mudae_likelist_not_for_you', self.lang), ephemeral=True
            )
            return False
        return True

    def build_embed(self) -> nextcord.Embed:
        description = "\n".join(self.pages[self.page]) or text('mudae_likelist_empty', self.lang)

        embed = nextcord.Embed(description=description, color=config.get('embed-color'))
        embed.set_author(
            name=text('mudae_likelist_title', self.lang).replace('%user%', self.display_name),
            icon_url=self.avatar_url
        )
        footer_text = text('mudae_likelist_footer', self.lang) \
            .replace('%current%', str(self.page + 1)) \
            .replace('%total%', str(len(self.pages))) \
            .replace('%characters%', str(self.character_count)) \
            .replace('%series%', str(self.series_count))
        embed.set_footer(text=footer_text)
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


def _build_likelist(lang: str, user: nextcord.abc.User, guild_id: int, allow_nsfw: bool) -> MudaeLikeListView:
    likes = get_user_likes(user.id, guild_id, allow_nsfw)
    return MudaeLikeListView(lang, user.id, user.display_name, _avatar_url(user), likes)


async def mudae_like_text(lang: str, message: nextcord.Message, action: str):
    query = message.content.strip()
    if not query:
        await message.reply(text(f'{ACTIONS[action]["key"]}_usage_error', lang), mention_author=False)
        return

    async def send(content, **kwargs):
        kwargs.pop('ephemeral', None)
        return await message.reply(content, mention_author=False, **kwargs)

    await _apply_like(
        lang, action, message.author, query, message.guild.id, _channel_allows_nsfw(message.channel), send
    )


async def mudae_like_slash(lang: str, interaction: nextcord.Interaction, action: str, query: str):
    async def send(content, **kwargs):
        await interaction.response.send_message(content, **kwargs)

    await _apply_like(
        lang, action, interaction.user, query, interaction.guild_id, _channel_allows_nsfw(interaction.channel), send
    )


async def mudae_likelist_text(lang: str, message: nextcord.Message):
    view = _build_likelist(lang, message.author, message.guild.id, _channel_allows_nsfw(message.channel))
    sent = await message.reply(embed=view.build_embed(), view=view, mention_author=False)
    view.bind_message(sent)


async def mudae_likelist_slash(lang: str, interaction: nextcord.Interaction):
    view = _build_likelist(lang, interaction.user, interaction.guild_id, _channel_allows_nsfw(interaction.channel))
    await interaction.response.send_message(embed=view.build_embed(), view=view)
    view.bind_interaction(interaction)


info = {
    "like": {
        "category": "mudae",
        "aliases": ["l"],
        "hidden_aliases": [],
        "available": ["slash_command", "text_command"],
        "dm_available": False,
        "visibility": "everyone",
        "user_permissions": [],
        "name": "like_name",
        "desc": "like_desc",
        "args": [
            {
                "name": "like_character_arg_name",
                "desc": "like_character_arg_desc",
                "required": True,
                "autocomplete": True,
            },
        ]
    },
    "likem": {
        "category": "mudae",
        "aliases": ["lm"],
        "hidden_aliases": [],
        "available": ["slash_command", "text_command"],
        "dm_available": False,
        "visibility": "everyone",
        "user_permissions": [],
        "name": "likem_name",
        "desc": "likem_desc",
        "args": [
            {
                "name": "likem_series_arg_name",
                "desc": "likem_series_arg_desc",
                "required": True,
                "autocomplete": True,
            },
        ]
    },
    "unlike": {
        "category": "mudae",
        "aliases": [],
        "hidden_aliases": [],
        "available": ["slash_command", "text_command"],
        "dm_available": False,
        "visibility": "everyone",
        "user_permissions": [],
        "name": "unlike_name",
        "desc": "unlike_desc",
        "args": [
            {
                "name": "unlike_character_arg_name",
                "desc": "unlike_character_arg_desc",
                "required": True,
                "autocomplete": True,
            },
        ]
    },
    "unlikem": {
        "category": "mudae",
        "aliases": [],
        "hidden_aliases": [],
        "available": ["slash_command", "text_command"],
        "dm_available": False,
        "visibility": "everyone",
        "user_permissions": [],
        "name": "unlikem_name",
        "desc": "unlikem_desc",
        "args": [
            {
                "name": "unlikem_series_arg_name",
                "desc": "unlikem_series_arg_desc",
                "required": True,
                "autocomplete": True,
            },
        ]
    },
    "likelist": {
        "category": "mudae",
        "aliases": [],
        "hidden_aliases": [],
        "available": ["slash_command", "text_command"],
        "dm_available": False,
        "visibility": "everyone",
        "user_permissions": [],
        "name": "likelist_name",
        "desc": "likelist_desc",
        "args": []
    },
}

locales = get_commands_locales(info)
cmd_like = CmdLocale("like", locales)
cmd_likem = CmdLocale("likem", locales)
cmd_unlike = CmdLocale("unlike", locales)
cmd_unlikem = CmdLocale("unlikem", locales)
cmd_likelist = CmdLocale("likelist", locales)


class MudaeLikeCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @check_ban()
    @checks.guild_only()
    @slash_command(
        name=cmd_like.name,
        description=cmd_like.description,
        name_localizations=cmd_like.name_localizations,
        description_localizations=cmd_like.description_localizations,
    )
    async def like_command(
        self, interaction: nextcord.Interaction,
        character: str = get_slash_option(cmd_like.arg(0)),
    ):
        await mudae_like_slash(get_lang(interaction), interaction, "like", character)

    @like_command.on_autocomplete("character")
    async def on_character_autocomplete(self, interaction: nextcord.Interaction, character: str):
        if not interaction.guild:
            await interaction.response.send_autocomplete({})
            return
        results = search_characters(character, interaction.guild.id, _channel_allows_nsfw(interaction.channel))
        await interaction.response.send_autocomplete(_autocomplete_options(results))

    @check_ban()
    @checks.guild_only()
    @slash_command(
        name=cmd_likem.name,
        description=cmd_likem.description,
        name_localizations=cmd_likem.name_localizations,
        description_localizations=cmd_likem.description_localizations,
    )
    async def likem_command(
        self, interaction: nextcord.Interaction,
        series: str = get_slash_option(cmd_likem.arg(0)),
    ):
        await mudae_like_slash(get_lang(interaction), interaction, "likem", series)

    @likem_command.on_autocomplete("series")
    async def on_series_autocomplete(self, interaction: nextcord.Interaction, series: str):
        if not interaction.guild:
            await interaction.response.send_autocomplete({})
            return
        results = search_series(series, interaction.guild.id, _channel_allows_nsfw(interaction.channel))
        await interaction.response.send_autocomplete(_autocomplete_options(results))

    @check_ban()
    @checks.guild_only()
    @slash_command(
        name=cmd_unlike.name,
        description=cmd_unlike.description,
        name_localizations=cmd_unlike.name_localizations,
        description_localizations=cmd_unlike.description_localizations,
    )
    async def unlike_command(
        self, interaction: nextcord.Interaction,
        character: str = get_slash_option(cmd_unlike.arg(0)),
    ):
        await mudae_like_slash(get_lang(interaction), interaction, "unlike", character)

    @unlike_command.on_autocomplete("character")
    async def on_liked_character_autocomplete(self, interaction: nextcord.Interaction, character: str):
        if not interaction.guild:
            await interaction.response.send_autocomplete({})
            return
        results = search_liked_characters(
            interaction.user.id, character, interaction.guild.id, _channel_allows_nsfw(interaction.channel)
        )
        await interaction.response.send_autocomplete(_autocomplete_options(results))

    @check_ban()
    @checks.guild_only()
    @slash_command(
        name=cmd_unlikem.name,
        description=cmd_unlikem.description,
        name_localizations=cmd_unlikem.name_localizations,
        description_localizations=cmd_unlikem.description_localizations,
    )
    async def unlikem_command(
        self, interaction: nextcord.Interaction,
        series: str = get_slash_option(cmd_unlikem.arg(0)),
    ):
        await mudae_like_slash(get_lang(interaction), interaction, "unlikem", series)

    @unlikem_command.on_autocomplete("series")
    async def on_liked_series_autocomplete(self, interaction: nextcord.Interaction, series: str):
        if not interaction.guild:
            await interaction.response.send_autocomplete({})
            return
        results = search_liked_series(
            interaction.user.id, series, interaction.guild.id, _channel_allows_nsfw(interaction.channel)
        )
        await interaction.response.send_autocomplete(_autocomplete_options(results))

    @check_ban()
    @checks.guild_only()
    @slash_command(
        name=cmd_likelist.name,
        description=cmd_likelist.description,
        name_localizations=cmd_likelist.name_localizations,
        description_localizations=cmd_likelist.description_localizations,
    )
    async def likelist_command(self, interaction: nextcord.Interaction):
        await mudae_likelist_slash(get_lang(interaction), interaction)


def setup(bot: commands.Bot):
    bot.add_cog(MudaeLikeCog(bot))


@checks.guild_only()
async def _message_handler_like(bot, message: nextcord.Message, lang: str, prefix_str: str):
    await mudae_like_text(lang, message, "like")


@checks.guild_only()
async def _message_handler_likem(bot, message: nextcord.Message, lang: str, prefix_str: str):
    await mudae_like_text(lang, message, "likem")


@checks.guild_only()
async def _message_handler_unlike(bot, message: nextcord.Message, lang: str, prefix_str: str):
    await mudae_like_text(lang, message, "unlike")


@checks.guild_only()
async def _message_handler_unlikem(bot, message: nextcord.Message, lang: str, prefix_str: str):
    await mudae_like_text(lang, message, "unlikem")


@checks.guild_only()
async def _message_handler_likelist(bot, message: nextcord.Message, lang: str, prefix_str: str):
    await mudae_likelist_text(lang, message)


_message_handlers = {
    "like": _message_handler_like,
    "likem": _message_handler_likem,
    "unlike": _message_handler_unlike,
    "unlikem": _message_handler_unlikem,
    "likelist": _message_handler_likelist,
}
