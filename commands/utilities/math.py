import nextcord
from nextcord.ext import commands, application_checks
from nextcord.application_command import slash_command, message_command
from utils.get_commands_locales import get_commands_locales
from utils.locale_helpers import CmdLocale, get_slash_option
from utils import config
from utils.settings.bot_ban import check_ban
from utils.languages import text
from utils.settings import prefix, lang
get_lang = lang.get_lang

import math
import random
import re

# Whitelist only safe math names
SAFE_GLOBALS = {
    "__builtins__": {},  # completely remove builtins
}

SAFE_LOCALS = {
    name: getattr(math, name)
    for name in dir(math)
    if not name.startswith("_")
}

def safe_eval(expr: str):
    return eval(expr, SAFE_GLOBALS, SAFE_LOCALS)

# utility helpers for formatting and evaluating expressions
_SUPERSCRIPT_MAP = str.maketrans('¹²³⁴⁵⁶⁷⁸⁹⁰', '1234567890')


def _sanitize_expression(expr: str) -> str:
    """Normalize characters that have a special meaning in math expressions."""
    return (
        expr
        .replace('x', '*')
        .replace('×', '*')
        .replace('÷', '/')
        .replace(',', '.')
        .replace('−', '-')
        .replace('^', '**')
    )


def _highlight_superscripts(expr: str) -> str:
    """Wrap any sequence of superscript digits in bold markers for display."""
    return re.sub(r'([¹²³⁴⁵⁶⁷⁸⁹⁰]+)', lambda m: f"**{m.group(1)}", expr)


def _prepare_for_eval(expr: str) -> str:
    """Return a python-evaluable expression with superscripts converted to digits and bold markers removed."""
    cleaned = expr.translate(_SUPERSCRIPT_MAP)
    # remove bold markers which were only for display
    return cleaned


def _compute_result(expr: str) -> str:
    """Returns the result of evaluating the sanitized expression.

    Raises whatever errors ``eval`` might raise so callers can handle them.
    """
    return str(safe_eval(expr))


async def math(lang: str, message: nextcord.Message):
    raw = message.content
    problem = _sanitize_expression(raw)
    if problem.strip() == "":
        await message.reply(text('math_error_empty', lang), mention_author=False)
        return

    # build display and evaluation strings
    display_expr = _highlight_superscripts(problem)
    eval_expr = _prepare_for_eval(display_expr)

    # pick a random emoji for fun
    calculator_emoji = (
        "<:calculator_uwu:995314847032029204>"
        if random.randint(1, 30) == 29
        else "<:calculator:995316296528969728>"
    )

    try:
        result = _compute_result(eval_expr)
        embed = nextcord.Embed(
            title=f"{calculator_emoji} • Calculatrice",
            colour=nextcord.Colour(0xae10ff),
            description=f"{text('math_problem', lang)}\n"
            f"```{eval_expr.replace(' ', '')}```\n"
            f"{text('math_result', lang)}\n"
            f"```{result}```",
        )
        await message.reply(embed=embed, mention_author=False)
    except NameError:
        await message.reply(text('math_error_name', lang), mention_author=False)
    except ValueError:
        await message.reply(text('math_error_value', lang), mention_author=False)
    except SyntaxError:
        await message.reply(text('math_error_syntax', lang), mention_author=False)
    except TypeError:
        await message.reply(text('math_error_type', lang), mention_author=False)
    return

async def math_slash(lang: str, interaction: nextcord.Interaction, content: str):
    """Handle slash command requests by reusing the same evaluation logic.

    ``content`` is the user-provided expression from the slash option.
    """
    problem = _sanitize_expression(content)
    if problem.strip() == "":
        await interaction.response.send_message(text('math_error_empty', lang), ephemeral=True)
        return

    display_expr = _highlight_superscripts(problem)
    eval_expr = _prepare_for_eval(display_expr)

    calculator_emoji = (
        "<:calculator_uwu:995314847032029204>"
        if random.randint(1, 30) == 29
        else "<:calculator:995316296528969728>"
    )

    try:
        result = _compute_result(eval_expr)
        embed = nextcord.Embed(
            title=f"{calculator_emoji} • Calculatrice",
            colour=nextcord.Colour(0xae10ff),
            description=f"{text('math_problem', lang)}\n"
            f"```{eval_expr.replace(' ', '')}```\n"
            f"{text('math_result', lang)}\n"
            f"```{result}```",
        )
        await interaction.response.send_message(embed=embed)
    except NameError:
        await interaction.response.send_message(text('math_error_name', lang), ephemeral=True)
    except ValueError:
        await interaction.response.send_message(text('math_error_value', lang), ephemeral=True)
    except SyntaxError:
        await interaction.response.send_message(text('math_error_syntax', lang), ephemeral=True)
    except TypeError:
        await interaction.response.send_message(text('math_error_type', lang), ephemeral=True)
    return


info = {
    "math": {
        "category": "utilities",
        "aliases": ["calc"],
        "hidden_aliases": ["calculate", "calculator", "calcul", "maths", "calculus", "mathématique", "mathématiques", "calculette"],
        "available": ["slash_command", "text_command"],
        "visibility": "everyone",
        "user_permissions": [],
        "name": "math_name",
        "desc": "math_desc",
        "args": [
            {
                "name": "math_arg_name",
                "desc": "math_arg_desc"
            }
        ]
    }
}

cmd = CmdLocale(list(info.keys())[0], get_commands_locales(info))

class MathCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @check_ban()
    @application_checks.has_permissions(**{perm: True for perm in cmd.user_permissions})
    @slash_command(
        name=cmd.name,
        description=cmd.description,
        name_localizations=cmd.name_localizations,
        description_localizations=cmd.description_localizations
    )
    async def math_command(self, interaction: nextcord.Interaction,
        text: str = get_slash_option(cmd.arg(0))
    ):
        await math_slash(get_lang(interaction), interaction, text)


def setup(bot: commands.Bot):
    bot.add_cog(MathCog(bot))

# Text command handler wrapper that adapts to message handler signature
async def _message_handler(bot, message: nextcord.Message, lang: str, prefix: str):
    await math(lang, message)
