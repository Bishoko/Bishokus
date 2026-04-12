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

from typing import Any
from difflib import SequenceMatcher
import utils.global_variables as gv

CATEGORIES = {
    "bot": {
        "emoji": "🤖",
        "locale_key": "category_bot"
    },
    "bot_owner": {
        "emoji": "👑",
        "locale_key": "category_bot_owner"
    },
    "fun": {
        "emoji": "🎲",
        "locale_key": "category_fun"
    },
    "moderation": {
        "emoji": "🛡️",
        "locale_key": "category_moderation"
    },
    "utilities": {
        "emoji": "🧩",
        "locale_key": "category_utilities"
    },
    "settings": {
        "emoji": "⚙️",
        "locale_key": "category_settings"
    },
}

COMMAND_MATCH_MIN_RATIO = 0.55


def _normalize_aliases(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(alias).strip().lower() for alias in value if str(alias).strip()]
    if isinstance(value, str):
        alias = value.strip().lower()
        return [alias] if alias else []
    return []


def _can_view_command(requester_id: int, command_data: dict) -> bool:
    visibility = command_data.get("visibility")
    if visibility in [None, "", "everyone"]:
        return True
    if visibility in ["bot_owner", "bow_owner"]:
        return requester_id == config.get("owner-id")
    return False


def _is_locale_allowed(command_data: dict, current_locale: str) -> bool:
    locale_only = command_data.get("locale_only")
    if not locale_only:
        return True

    allowed_locales = locale_only if isinstance(locale_only, (list, tuple, set)) else [locale_only]
    current = str(current_locale or "").lower().replace("_", "-")
    current_prefix = current[:2]

    for allowed_locale in allowed_locales:
        allowed = str(allowed_locale).lower().replace("_", "-")
        if allowed == current:
            return True
        if allowed[:2] and allowed[:2] == current_prefix:
            return True

    return False


def _resolve_localized_value(value: Any, lang: str, fallback: str = "") -> str:
    if isinstance(value, dict):
        if lang in value and value[lang]:
            return str(value[lang])

        lang_prefix = lang.lower()[:2]
        for locale, localized_value in value.items():
            if str(locale).lower().startswith(lang_prefix) and localized_value:
                return str(localized_value)

        for localized_value in value.values():
            if localized_value:
                return str(localized_value)

        return fallback

    if isinstance(value, str):
        localized = text(value, lang)
        return localized if localized else fallback

    if value is None:
        return fallback

    return str(value)


def _get_local_name(command_name: str, command_data: dict, lang: str) -> str:
    return _resolve_localized_value(command_data.get("name", command_name), lang, command_name)


def _get_full_display_name(command_name: str, command_data: dict, lang: str, commands_info: dict) -> str:
    parent_name = command_data.get("parent")
    local_name = _get_local_name(command_name, command_data, lang)
    if parent_name and parent_name in commands_info:
        return f"{_get_full_display_name(parent_name, commands_info[parent_name], lang, commands_info)} {local_name}"
    return local_name


def _get_root_category(command_name: str, commands_info: dict) -> str:
    command_data = commands_info.get(command_name, {})
    parent_name = command_data.get("parent")
    if parent_name and parent_name in commands_info:
        return _get_root_category(parent_name, commands_info)

    category = command_data.get("category", "other")
    if category in CATEGORIES:
        return category
    if " " in category:
        root_category = category.split(" ", 1)[0]
        if root_category in CATEGORIES:
            return root_category
    return category


def _get_category_name(category: str, lang: str) -> str:
    category_data = CATEGORIES.get(category, {})
    emoji = category_data.get("emoji", "")
    locale_key = category_data.get("locale_key")
    if locale_key:
        return f"{emoji} {text(locale_key, lang)}"
    return f"{emoji} {category}".strip()


def _get_display_name(command_name: str, command_data: dict, lang: str) -> str:
    commands_info = gv.get("commands_info") or {}
    return _get_full_display_name(command_name, command_data, lang, commands_info)


def _get_args_usage(command_data: dict, lang: str) -> str:
    args = command_data.get("args", []) or []
    parts = []
    for arg in args:
        if not isinstance(arg, dict):
            continue

        arg_name_key = arg.get("name", "arg")
        arg_name = _resolve_localized_value(arg_name_key, lang, "arg")
        required = arg.get("required", True)
        if required:
            parts.append(f"<{arg_name}>")
        else:
            parts.append(f"[{arg_name}]")

    return " ".join(parts)


def _get_availability_label(command_data: dict, lang: str) -> str:
    available = command_data.get("available", [])
    has_context = "context_command" in available
    has_slash = "slash_command" in available
    has_text = "text_command" in available

    if has_text and has_context and not has_slash:
        return text('help_command_availability_both_text_and_context', lang)
    if has_slash and has_text:
        return text('help_command_availability_both', lang)
    if has_text:
        return text('help_command_availability_text', lang)
    if has_slash:
        return text('help_command_availability_slash', lang)
    if has_context:
        return text('help_command_availability_context', lang)
    return ""


def _get_command_usage(command_name: str, command_data: dict, commands_info: dict, lang: str, command_prefix: str) -> str:
    full_name = _get_full_display_name(command_name, command_data, lang, commands_info)
    args_usage = _get_args_usage(command_data, lang)
    args_suffix = f" {args_usage}" if args_usage else ""

    available = command_data.get("available", [])
    has_slash = "slash_command" in available
    has_text = "text_command" in available
    has_context = "context_command" in available

    if has_text and has_context and not has_slash:
        return f"`{command_prefix}{full_name.lower()}{args_suffix}`\n`{text('help_command_right_click_instructions', lang)} {full_name}`"
    if has_slash and has_text:
        return f"`/{full_name}{args_suffix}`"
    if has_text:
        return f"`{command_prefix}{full_name.lower()}{args_suffix}`"
    if has_slash:
        return f"`/{full_name}{args_suffix}`"
    if has_context:
        return f"`{text('help_command_right_click_instructions', lang)} {full_name}{args_suffix}`"
    return f"`{full_name}{args_suffix}`"


def _resolve_command(query: str, commands_info: dict, lang: str, requester_id: int):
    normalized_query = query.strip().lower()
    if not normalized_query:
        return None, None

    for command_name, command_data in commands_info.items():
        if not _can_view_command(requester_id, command_data):
            continue
        if not _is_locale_allowed(command_data, lang):
            continue

        aliases = [command_name.lower()]
        aliases.extend(_normalize_aliases(command_data.get("aliases", [])))
        aliases.extend(_normalize_aliases(command_data.get("hidden_aliases", [])))
        aliases.extend(_normalize_aliases(command_data.get("aliases_sub_only", [])))

        display_name = _get_full_display_name(command_name, command_data, lang, commands_info).lower()

        if normalized_query in aliases or normalized_query == display_name:
            return command_name, command_data

    return None, None


def _score_command_target(query: str, target: str) -> float:
    if not target:
        return 0.0

    if query and query == target:
        return 1.0

    similarity = SequenceMatcher(None, query, target).ratio() if query else 0.0
    if query and target.startswith(query):
        similarity += 0.35
    elif query and query in target:
        similarity += 0.2

    return min(1.0, similarity)


def _rank_command_matches(query: str, commands_info: dict, lang: str, requester_id: int, min_ratio: float = COMMAND_MATCH_MIN_RATIO) -> list[dict]:
    normalized_query = (query or "").strip().lower()
    ranked_matches = []

    for command_name, command_data in commands_info.items():
        if not _can_view_command(requester_id, command_data):
            continue
        if not _is_locale_allowed(command_data, lang):
            continue

        display_name = _get_full_display_name(command_name, command_data, lang, commands_info)
        display_target = display_name.lower()

        aliases = _normalize_aliases(command_data.get("aliases", []))
        aliases_sub_only = _normalize_aliases(command_data.get("aliases_sub_only", []))
        hidden_aliases = _normalize_aliases(
            command_data.get("hidden_aliases", command_data.get("hiddel_aliases", []))
        )

        alias_targets = [command_name.lower(), *aliases, *aliases_sub_only]
        hidden_targets = hidden_aliases
        all_targets = [display_target, *alias_targets, *hidden_targets]

        exact_alias = normalized_query in alias_targets if normalized_query else False
        exact_hidden = normalized_query in hidden_targets if normalized_query else False
        exact_display = normalized_query == display_target if normalized_query else False
        has_exact = exact_alias or exact_hidden or exact_display

        contains_match = (not normalized_query) or any(normalized_query in target for target in all_targets)
        best_raw_ratio = max(
            (SequenceMatcher(None, normalized_query, target).ratio() for target in all_targets),
            default=0.0,
        ) if normalized_query else 1.0

        if has_exact:
            best_raw_ratio = 1.0

        if normalized_query and not has_exact and not contains_match and best_raw_ratio < min_ratio:
            continue

        alias_score = max((_score_command_target(normalized_query, target) for target in alias_targets), default=0.0)
        hidden_score = max((_score_command_target(normalized_query, target) for target in hidden_targets), default=0.0)
        display_score = _score_command_target(normalized_query, display_target)

        if exact_alias:
            priority = 0
            best_score = 1.0
        elif exact_hidden:
            priority = 1
            best_score = 1.0
        elif exact_display:
            priority = 2
            best_score = 1.0
        elif alias_score >= hidden_score and alias_score >= display_score:
            priority = 0
            best_score = alias_score
        elif hidden_score >= display_score:
            priority = 1
            best_score = hidden_score
        else:
            priority = 2
            best_score = display_score

        ranked_matches.append({
            "exact": has_exact,
            "priority": priority,
            "score": best_score,
            "raw_ratio": best_raw_ratio,
            "display_name": display_name,
            "command_name": command_name,
            "command_data": command_data,
        })

    ranked_matches.sort(
        key=lambda item: (
            0 if item["exact"] else 1,
            item["priority"],
            -item["score"],
            -item["raw_ratio"],
            item["display_name"].lower(),
        )
    )
    return ranked_matches


def _resolve_command_best_match(query: str, commands_info: dict, lang: str, requester_id: int, min_ratio: float = COMMAND_MATCH_MIN_RATIO):
    ranked_matches = _rank_command_matches(query, commands_info, lang, requester_id, min_ratio=min_ratio)
    if not ranked_matches:
        return None, None, 0.0

    top_match = ranked_matches[0]
    return top_match["command_name"], top_match["command_data"], top_match["raw_ratio"]


def _render_command_tree(command_name: str, commands_info: dict, children_by_parent: dict, lang: str, command_prefix: str, level: int = 0) -> list[str]:
    command_data = commands_info[command_name]
    command_usage = _get_command_usage(command_name, command_data, commands_info, lang, command_prefix)
    availability_label = _get_availability_label(command_data, lang)
    availability_label = "" if availability_label == text('help_command_availability_both', lang) else availability_label
    command_desc = _resolve_localized_value(command_data.get("desc", ""), lang, "")
    indent = "" * level # can't find a great character for this so it's unused for now
    
    if availability_label == text('help_command_availability_both_text_and_context', lang):
        line = f"{indent}**{command_usage.lower()} | {command_usage.replace(command_prefix, text('help_command_right_click_instructions', lang))}"
    else:
        label = f" [{availability_label}]" if availability_label else ""
        line = f"{indent}**{command_usage}:{label}"

    line += f" **{command_desc}" if command_desc else "**"
    
    lines = [line]
    for child_name in sorted(children_by_parent.get(command_name, []), key=lambda name: name.lower()):
        lines.extend(_render_command_tree(child_name, commands_info, children_by_parent, lang, command_prefix, level + 1))
    return lines


def _build_command_pages(commands_info: dict, lang: str, requester_id: int, command_prefix: str) -> list[dict]:
    visible_commands = {}
    for command_name, command_data in commands_info.items():
        available = command_data.get("available", [])
        if "slash_command" not in available and "text_command" not in available:
            continue
        if not _can_view_command(requester_id, command_data):
            continue
        if not _is_locale_allowed(command_data, lang):
            continue
        visible_commands[command_name] = command_data

    children_by_parent = {}
    grouped = {}
    for command_name, command_data in visible_commands.items():
        parent_name = command_data.get("parent")
        if parent_name in visible_commands:
            children_by_parent.setdefault(parent_name, []).append(command_name)

        root_category = _get_root_category(command_name, visible_commands)
        grouped.setdefault(root_category, []).append(command_name)

    preferred_order = [category for category in CATEGORIES if category in grouped]
    extra_categories = sorted(category for category in grouped if category not in CATEGORIES)
    categories = preferred_order + extra_categories
    pages = []
    for category in categories:
        top_level_commands = []
        for command_name in grouped[category]:
            parent_name = visible_commands[command_name].get("parent")
            if parent_name not in visible_commands or _get_root_category(parent_name, visible_commands) != category:
                top_level_commands.append(command_name)

        if not top_level_commands:
            continue

        lines = []
        for command_name in sorted(top_level_commands, key=lambda name: name.lower()):
            lines.extend(_render_command_tree(command_name, visible_commands, children_by_parent, lang, command_prefix))
        
        lines[0] = f">>> {lines[0]}"
        
        pages.append({
            "title": _get_category_name(category, lang) + " - " + text("help_embed_title", lang),
            "description": text("help_embed_desc", lang),
            "category": category,
            "fields": [{
                "name": "",
                "value": "\n".join(lines) if lines else "-",
                "inline": False,
            }],
        })

    return pages if pages else [{
        "title": text("help_embed_title", lang),
        "description": text("help_no_commands", lang),
        "category": "-",
        "fields": [],
    }]


def _help_command_embed(bot: commands.Bot, lang: str, command_name: str, command_data: dict, requester_id: int = None) -> nextcord.Embed:
    display_name = _get_display_name(command_name, command_data, lang)
    description = _resolve_localized_value(command_data.get("desc", ""), lang, "")
    aliases = _normalize_aliases(command_data.get("aliases", []))
    hidden_aliases = _normalize_aliases(command_data.get("hidden_aliases", []))
    availability_label = _get_availability_label(command_data, lang)
    root_category = _get_root_category(command_name, gv.get("commands_info") or {})
    command_prefix = config.get("default-prefix")
    usage = _get_command_usage(command_name, command_data, gv.get("commands_info") or {}, lang, command_prefix)

    embed = nextcord.Embed(
        title=text("help_command_embed_title", lang).replace("%command%", display_name),
        description=description,
        color=config.get("embed-color")
    )

    embed.add_field(name=text("help_command_category", lang), value=_get_category_name(root_category, lang), inline=True)
    embed.add_field(name=text("help_command_availability", lang), value=availability_label, inline=True)
    embed.add_field(name=text("help_command_usage", lang), value=usage, inline=False)
    embed.add_field(name=text("help_command_aliases", lang), value=", ".join(aliases) if aliases else "-", inline=False)
    embed.add_field(name=text("help_command_hidden_aliases", lang), value=", ".join(hidden_aliases) if hidden_aliases else "-", inline=False)

    if command_data.get("has_subcommands", False):
        commands_info = gv.get("commands_info") or {}
        subcommands = []
        for child_name, child_data in commands_info.items():
            if child_data.get("parent") != command_name:
                continue
            if requester_id is not None and not _can_view_command(requester_id, child_data):
                continue
            if not _is_locale_allowed(child_data, lang):
                continue

            sub_name = _get_local_name(child_name, child_data, lang)
            sub_desc = _resolve_localized_value(child_data.get("desc", ""), lang, "")
            line = f"`{sub_name}`"
            if sub_desc:
                line += f" - {sub_desc}"
            subcommands.append(line)

        if subcommands:
            embed.add_field(
                name=text("help_command_subcommands", lang),
                value="\n".join(sorted(subcommands, key=str.lower)),
                inline=False
            )

    return embed


class HelpView(nextcord.ui.View):
    def __init__(self, bot: commands.Bot, lang: str, requester_id: int, pages: list[dict]):
        super().__init__(timeout=None)
        self.bot = bot
        self.lang = lang
        self.requester_id = requester_id
        self.pages = pages
        self.page = 0

        if len(self.pages) > 1:
            options = [
                nextcord.SelectOption(
                    label=(_get_category_name(page_data.get("category", "-"), self.lang)[:100] or "-"),
                    value=str(index),
                    default=(index == 0)
                )
                for index, page_data in enumerate(self.pages[:25])
            ]
            self.category_select = nextcord.ui.Select(
                custom_id="help_category_select",
                placeholder=text("help_select_placeholder", self.lang),
                min_values=1,
                max_values=1,
                options=options
            )
            self.category_select.callback = self._on_category_select
            self.add_item(self.category_select)

        self._refresh_buttons()

    def to_components(self) -> list[dict]:
        current_page = self.pages[self.page]
        title = current_page.get("title", "")
        description = current_page.get("description", "")
        fields = current_page.get("fields", [])

        container_components: list[dict] = [
            {"type": 10, "content": f"## {title}\n{description}"},
        ]

        for field in fields:
            container_components.append({"type": 14, "divider": True, "spacing": 1})
            container_components.append({"type": 10, "content": field['value']})

        if hasattr(self, "category_select"):
            container_components.append({"type": 14, "divider": True, "spacing": 1})
            container_components.append({
                "type": 1,
                "components": [self.category_select.to_component_dict()]
            })

        footer_text = text("help_page_footer", self.lang).replace(
            "%current%", str(self.page + 1)
        ).replace("%total%", str(len(self.pages)))
        container_components.append({"type": 10, "content": f"-# {footer_text}"})

        container = {
            "type": 17,
            "accent_color": config.get("embed-color"),
            "components": container_components
        }

        nav_row = {
            "type": 1,
            "components": [
                self.previous_button.to_component_dict(),
                self.next_button.to_component_dict()
            ]
        }

        return [container, nav_row]

    def _refresh_buttons(self):
        self.previous_button.disabled = self.page == 0
        self.next_button.disabled = self.page >= len(self.pages) - 1
        if hasattr(self, "category_select"):
            for option in self.category_select.options:
                option.default = option.value == str(self.page)

    async def interaction_check(self, interaction: nextcord.Interaction) -> bool:
        if interaction.user.id != self.requester_id:
            await interaction.response.send_message(text("help_not_for_you", self.lang), ephemeral=True)
            return False
        return True

    async def _on_category_select(self, interaction: nextcord.Interaction):
        selected_value = self.category_select.values[0]
        self.page = max(0, min(len(self.pages) - 1, int(selected_value)))
        self._refresh_buttons()
        await interaction.response.edit_message(view=self)

    @nextcord.ui.button(label="◀", style=nextcord.ButtonStyle.secondary)
    async def previous_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        self.page = max(0, self.page - 1)
        self._refresh_buttons()
        await interaction.response.edit_message(view=self)

    @nextcord.ui.button(label="▶", style=nextcord.ButtonStyle.secondary)
    async def next_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        self.page = min(len(self.pages) - 1, self.page + 1)
        self._refresh_buttons()
        await interaction.response.edit_message(view=self)


async def help_text(bot: commands.Bot, lang: str, message: nextcord.Message, command_query: str, command_prefix: str):
    commands_info = gv.get("commands_info") or {}

    if command_query:
        command_name, command_data, _ = _resolve_command_best_match(
            command_query,
            commands_info,
            lang,
            message.author.id,
            min_ratio=COMMAND_MATCH_MIN_RATIO,
        )
        if command_data:
            embed = _help_command_embed(bot, lang, command_name, command_data, requester_id=message.author.id)
            usage = _get_command_usage(command_name, command_data, commands_info, lang, command_prefix)
            if lang == "fr":
                usage += "\n" + _get_command_usage(command_name, command_data, commands_info, "en_US", command_prefix) + " :flag_gb:"
            embed.set_field_at(2,
                name=text("help_command_usage", lang),
                value=usage,
                inline=False
            )
            await message.reply(embed=embed, mention_author=False)
            return

        await message.reply(text("help_command_not_found", lang).replace("%command%", command_query), mention_author=False)
        return

    pages = _build_command_pages(commands_info, lang, message.author.id, command_prefix)
    view = HelpView(bot, lang, message.author.id, pages)
    flags = nextcord.MessageFlags()
    flags.is_components_v2 = True
    await message.reply(view=view, flags=flags, mention_author=False)


async def help_slash(bot: commands.Bot, lang: str, interaction: nextcord.Interaction, command_query: str = None, ephemeral: bool=True):
    commands_info = gv.get("commands_info") or {}
    command_prefix = prefix.get(interaction.guild.id) if interaction.guild else config.get("default-prefix")

    if command_query:
        command_name, command_data = _resolve_command(command_query, commands_info, lang, interaction.user.id)
        if command_data:
            embed = _help_command_embed(bot, lang, command_name, command_data, requester_id=interaction.user.id)
            usage = _get_command_usage(command_name, command_data, commands_info, lang, command_prefix)
            embed.set_field_at(2, name=text("help_command_usage", lang), value=usage, inline=False)
            await interaction.response.send_message(
                embed=embed,
                ephemeral=ephemeral
            )
            return

        await interaction.response.send_message(
            text("help_command_not_found", lang).replace("%command%", command_query),
            ephemeral=ephemeral
        )
        return

    pages = _build_command_pages(commands_info, lang, interaction.user.id, command_prefix)
    view = HelpView(bot, lang, interaction.user.id, pages)
    flags = nextcord.MessageFlags()
    flags.is_components_v2 = True
    await interaction.response.send_message(view=view, flags=flags, ephemeral=ephemeral)


info = {
    "help": {
        "category": "bot",
        "aliases": ["h"],
        "hidden_aliases": ["commands", "command", "aide"],
        "available": ["slash_command", "text_command"],
        "visibility": "everyone",
        "user_permissions": [],
        "name": "help_name",
        "desc": "help_desc",
        "args": [
            {
                "name": "help_arg_name",
                "desc": "help_arg_desc",
                "required": False,
                "autocomplete": True,
            },
            { # TODO: make this modular using locale_helpers so we can add it to other commands if needed
                "name": "arg_ephemeral_name",
                "desc": "arg_ephemeral_desc",
                "required": False,
                "default": "1",
                "choices": {
                    "arg_ephemeral_true": "1",
                    "arg_ephemeral_false": "0",
                }
            },
        ]
    }
}

cmd = CmdLocale(list(info.keys())[0], get_commands_locales(info))

class HelpCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    async def command_autocomplete(self, interaction: nextcord.Interaction, current: str):
        lang = get_lang(interaction)
        commands_info = gv.get("commands_info") or {}
        scored_results = _rank_command_matches(
            current,
            commands_info,
            lang,
            interaction.user.id,
            min_ratio=COMMAND_MATCH_MIN_RATIO,
        )

        choices = {}
        for result in scored_results:
            display_name = result["display_name"]
            command_name = result["command_name"]
            if display_name in choices:
                continue
            choices[display_name] = command_name
            if len(choices) >= 25:
                break

        return choices

    @check_ban()
    @slash_command(
        name=cmd.name,
        description=cmd.description,
        name_localizations=cmd.name_localizations,
        description_localizations=cmd.description_localizations
    )
    async def help_command(self, interaction: nextcord.Interaction,
        command: str = get_slash_option(cmd.arg(0)),
        ephemeral: str = get_slash_option(cmd.arg(1)),
    ):
        await help_slash(self.bot, get_lang(interaction), interaction, command, bool(int(ephemeral)))
    
    @help_command.on_autocomplete("command")
    async def on_command_autocomplete(self, interaction: nextcord.Interaction, command: str):
        await interaction.response.send_autocomplete(await self.command_autocomplete(interaction, command))


def setup(bot: commands.Bot):
    bot.add_cog(HelpCog(bot))

async def _message_handler(bot, message: nextcord.Message, lang: str, prefix: str):
    await help_text(bot, lang, message, message.content.strip(), prefix)
