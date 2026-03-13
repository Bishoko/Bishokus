import json
import nextcord

from utils.get_commands_locales import get_commands_locales
from utils.languages import text

# pull default language for labels from config; used by ArgLocale/CmdLocale
with open('config/config.json', 'r', encoding='utf-8') as config_file:
    _cfg = json.load(config_file)
    default_locale = _cfg['default-slash-locale']


class ArgLocale:
    """Wrapper around a single argument's locale data.

    The object provides convenient properties for consumers that are
    localized to the configured default language.
    """

    def __init__(self, data: dict):
        self._d = data

    @property
    def name(self) -> str:
        return self._d['name'][default_locale]

    @property
    def description(self) -> str:
        return self._d['desc'][default_locale]

    @property
    def name_localizations(self) -> dict:
        return self._d['name']

    @property
    def description_localizations(self) -> dict:
        return self._d['desc']

    @property
    def default(self):
        # When required is not True and the user doesn't provide a value for this Option, this value is given instead.
        return self._d.get('default') or nextcord.utils.MISSING
    
    @property
    def choices(self):
        raw_choices = self._d.get('choices')
        if not isinstance(raw_choices, dict):
            return raw_choices

        return {
            text(str(choice_key), default_locale): value
            for choice_key, value in raw_choices.items()
        }

    @property
    def choice_localizations(self):
        raw_choices = self._d.get('choices')
        if not isinstance(raw_choices, dict):
            return None

        lang_codes = list(self.name_localizations.keys())
        if default_locale not in lang_codes:
            lang_codes.append(default_locale)

        return {
            text(str(choice_key), default_locale): {
                lang: text(str(choice_key), lang)
                for lang in lang_codes
            }
            for choice_key in raw_choices
        }

    @property
    def required(self):
        return self._d.get('required', True)

    @property
    def autocomplete(self):
        return self._d.get('autocomplete', False)

    @property
    def min_length(self):
        return self._d.get('min_length')

    @property
    def max_length(self):
        return self._d.get('max_length')

    @property
    def min_value(self):
        return self._d.get('min_value')

    @property
    def max_value(self):
        return self._d.get('max_value')


class CmdLocale:
    """Accessor for command-level locale information."""

    def __init__(self, name: str, locales: dict):
        self._d = locales[name]

    @property
    def name(self) -> str:
        return self._d['name'][default_locale]

    @property
    def description(self) -> str:
        return self._d['desc'][default_locale]

    @property
    def name_localizations(self) -> dict:
        return self._d['name']

    @property
    def description_localizations(self) -> dict:
        return self._d['desc']

    @property
    def user_permissions(self) -> list:
        return self._d.get('user_permissions', [])

    def arg(self, index: int) -> ArgLocale:
        return ArgLocale(self._d['args'][index])



def get_slash_option(cmd_or_arg, arg_index=None, locales=None, custom_choices=None):
    """Return a preconfigured :class:`nextcord.SlashOption`.

    Callers may pass either an ``ArgLocale`` instance or a command name plus
    an argument index (legacy).  ``custom_choices`` allows overriding the
    choices dictionary for a specific invocation.
    """

    if isinstance(cmd_or_arg, ArgLocale):
        arg = cmd_or_arg
    else:
        # legacy path: build an ArgLocale from command name and index
        if locales is None:
            locales = get_commands_locales()
        arg = ArgLocale(locales[cmd_or_arg]['args'][arg_index])

    use_custom_choices = custom_choices is not None
    return nextcord.SlashOption(
        name=arg.name,
        name_localizations=arg.name_localizations,
        description=arg.description,
        description_localizations=arg.description_localizations,
        default=arg.default,
        choices=custom_choices if use_custom_choices else arg.choices,
        choice_localizations=None if use_custom_choices else arg.choice_localizations,
        required=arg.required,
        autocomplete=arg.autocomplete,
        min_length=arg.min_length,
        max_length=arg.max_length,
        min_value=arg.min_value,
        max_value=arg.max_value,
    )
