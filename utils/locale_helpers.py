import json
import nextcord

from utils.get_commands_locales import get_commands_locales

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
    def choices(self):
        return self._d.get('choices')

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

    return nextcord.SlashOption(
        name=arg.name,
        name_localizations=arg.name_localizations,
        description=arg.description,
        description_localizations=arg.description_localizations,
        choices=custom_choices or arg.choices,
        required=arg.required,
        autocomplete=arg.autocomplete,
        min_length=arg.min_length,
        max_length=arg.max_length
    )
