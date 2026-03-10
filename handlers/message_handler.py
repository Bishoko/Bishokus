import nextcord

from utils.config import config
from utils.get_commands_locales import get_commands_locales
from utils.languages import text
from utils.settings import prefix
from utils.settings import lang as language
from utils.settings.bot_ban import check_ban_on_message
from utils.normalize_wordplay import normalize_wordplay
from utils.sql.get import get
import utils.global_variables as gv

from unidecode import unidecode

def _normalize_aliases(value) -> list[str]:
    if isinstance(value, list):
        return [str(alias).strip().lower() for alias in value if str(alias).strip()]
    if isinstance(value, str):
        alias = value.strip().lower()
        return [alias] if alias else []
    return []


def _get_command_aliases(command_name: str, command_data: dict, parent_name: str = None) -> list[str]:
    aliases = [command_name.lower().strip()]

    if parent_name:
        parent_prefix = f"{parent_name.lower().strip()} "
        command_name_lower = command_name.lower().strip()
        if command_name_lower.startswith(parent_prefix):
            local_name = command_name_lower[len(parent_prefix):].strip()
            if local_name:
                aliases.append(local_name)

    aliases.extend(_normalize_aliases(command_data.get('aliases', [])))
    aliases.extend(_normalize_aliases(command_data.get('hidden_aliases', [])))

    if parent_name is not None:
        aliases.extend(_normalize_aliases(command_data.get('aliases_sub_only', [])))

    seen = set()
    unique_aliases = []
    for alias in aliases:
        if alias and alias not in seen:
            unique_aliases.append(alias)
            seen.add(alias)

    return unique_aliases


def _extract_matched_prefix(content: str, aliases: list[str]) -> str | None:
    content = content.strip()
    if not content:
        return None

    content_lower = content.lower()
    for alias in sorted(aliases, key=len, reverse=True):
        if not content_lower.startswith(alias):
            continue

        if len(content_lower) == len(alias) or content_lower[len(alias)] == ' ':
            return content[:len(alias)]

    return None


def _is_locale_allowed(command_data: dict, current_locale: str) -> bool:
    locale_only = command_data.get('locale_only')
    if not locale_only:
        return True

    allowed_locales = locale_only if isinstance(locale_only, (list, tuple, set)) else [locale_only]

    for allowed_locale in allowed_locales:
        if allowed_locale == current_locale:
            return True

    return False


def _resolve_command_from_content(content: str, commands_info: dict) -> tuple[str | None, str]:
    children_by_parent = {}
    standalone_candidates = []
    for command_name, command_data in commands_info.items():
        parent = command_data.get('parent')
        children_by_parent.setdefault(parent, []).append((command_name, command_data))

        if parent is not None:
            standalone_candidates.append((command_name, command_data))

    remaining = content.strip()
    current_parent = None
    resolved_command_name = None

    while remaining:
        candidates = children_by_parent.get(current_parent, [])

        if current_parent is None:
            candidates = [*candidates, *standalone_candidates]

        matched = None

        for command_name, command_data in candidates:
            aliases = _get_command_aliases(command_name, command_data, current_parent)
            matched_prefix = _extract_matched_prefix(remaining, aliases)
            if not matched_prefix:
                continue

            if matched is None or len(matched_prefix) > len(matched[2]):
                matched = (command_name, command_data, matched_prefix)

        if matched is None:
            break

        command_name, command_data, matched_prefix = matched
        resolved_command_name = command_name
        remaining = remaining[len(matched_prefix):].strip()

        if not command_data.get('has_subcommands', False):
            break

        current_parent = command_name

    return resolved_command_name, remaining

_get_wordplay = None

async def handle_message(bot, message: nextcord.Message):
    global _get_wordplay
    
    # Initialize lazy-loaded function references
    if _get_wordplay is None:
        _get_wordplay = gv.get("get_wordplay")
    
    p = prefix.get(message.guild.id) if message.guild else config.get('default-prefix')
    
    if message.author.bot:
        return
    
    # Check if the message mentions the bot
    bot_mention = f'<@{bot.user.id}>'
    if message.content == bot_mention or (bot_mention in message.content.lstrip('!') and not message.content.startswith(bot_mention)):
        if not await check_ban_on_message(message):
            return
        await message.reply(
            text('bot_mention', language.get(message.guild.id, message.author.id)).replace('%prefix%', p),
            mention_author=False
        )
    
    message_content_backup = message.content
    
    if message.content.startswith(p) or message.content.lstrip('!').startswith(f'<@{bot.application_id}>'):
        message.content = message.content.removeprefix(p).removeprefix(f'<@{bot.application_id}>').removeprefix(f'<@!{bot.application_id}>').strip()        
        if not len(message.content) > 0:
            return
        lang = language.get(message.guild.id if message.guild else 0, message.author.id)
        
        # Get commands info and message handlers from global variables
        commands_info = gv.get("commands_info")
        message_handlers = gv.get("message_handlers") or {}
        
        if commands_info is None:
            commands_info = get_commands_locales()
            print(f"Loaded commands locales")
        
        # Remove accents from message.content
        message.content = unidecode(message.content)
        
        resolved_command_name, remaining_content = _resolve_command_from_content(message.content, commands_info)

        if resolved_command_name is None:
            print(f"Unknown command: {message.content.split()[0].lower()}")
            return

        command_info = commands_info.get(resolved_command_name, {})
        if not _is_locale_allowed(command_info, lang):
            return

        if not await check_ban_on_message(message):
            return

        message.content = remaining_content

        if resolved_command_name in message_handlers:
            handler = message_handlers[resolved_command_name]
            await handler(bot, message, lang, p)
            # Restore message.content after handling to preserve it for other handlers
            message.content = message_content_backup
        else:
            print(f"No text command handler found for: {resolved_command_name}")


    # Wordplay handling
    if not _get_wordplay:
        return
    
    normalized = normalize_wordplay(message.content)
    if normalized and message.guild and get("wordplay_enabled", message.guild.id):
        await message.reply(_get_wordplay(normalized), mention_author=False)

