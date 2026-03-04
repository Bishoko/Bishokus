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

import aiohttp
from blagues_api import BlaguesAPI, BlagueType
from difflib import SequenceMatcher

blagues_api = BlaguesAPI(config.get('api-keys')['blagues'])

# Mapping of joke types for French blagues
FRENCH_TYPE_TRANSLATIONS = {
    'dark': 'humour noir',
    'global': 'normale',
    'dev': 'développeurs',
    'beauf': 'beauf',
    'limit': 'limite',
    'blond': 'blondes'
}

# Mapping of joke categories to BlagueType for French
FRENCH_CATEGORY_MAP = {
    BlagueType.DARK: [BlagueType.DARK, 'noir', 'humour_noir', 'humournoir', 'hn', 'nwar', 'n'],
    BlagueType.DEV: [BlagueType.DEV, 'developeurs', 'developement', 'developeur', 'code', 'coding', 'codage', 'programation', 'programeur', 'programer', 'd'], # misspellings
    BlagueType.GLOBAL: [BlagueType.GLOBAL, 'normal', 'normale', 'g'],
    BlagueType.BEAUF: [BlagueType.BEAUF, 'beaf', 'bauf', 'bauf', 'bæuf', 'b'],
    BlagueType.BLONDES: [BlagueType.BLONDES,'blond', 'blonde', 'bl', 'bld'],
    BlagueType.LIMIT: [BlagueType.LIMIT, 'limite', '18+', '18', 'adult', 'adulte', 'a', 'l'],
}

# English joke categories for jokeapi.dev
ENGLISH_CATEGORY_MAP = {
    'programming': ['programing', 'program', 'prog', 'code', 'coding', 'coder', 'programer', 'p'],
    'misc': ['miscellaneous', 'general', 'any', 'misc', 'other', 'm'],
    'dark': ['dark', 'dark humor', 'darkhumor', 'dh', 'darkhumour', 'dark humour', 'darkhumour', 'darkh', 'd'],
    'pun': ['pun', 'puns', 'play on words', 'wordplay', 'punny', 'p'],
    'spooky': ['spooky', 'ghost', 'haunted', 'sp', 's'],
    'christmas': ['christmas', 'xmas', 'holiday', 'christ', 'xm', 'c',]
}

# Autocomplete choices for French jokes
FRENCH_CATEGORIES = {
    'Aléatoire': 'random',
    'Humour noir': 'dark',
    'Développeurs': 'dev',
    'Normale': 'normale',
    'Beauf': 'beauf',
    'Limite (18+)': 'limite',
    'Blondes': 'blondes'
}

# Autocomplete choices for English jokes
ENGLISH_CATEGORIES = {
    'Random': 'random',
    'Programming': 'programming',
    'Miscellaneous': 'misc',
    'Dark': 'dark',
    'Pun': 'pun',
    'Spooky': 'spooky',
    'Christmas': 'christmas'
}


async def _get_category(input_category: str, category_map: dict):
    """Helper function to get the category key from user input using similarity matching"""
    input_category = input_category.lower()
    
    best_match = None
    highest_ratio = 0.0
    
    for key, aliases in category_map.items():
        for alias in aliases:
            ratio = SequenceMatcher(None, input_category, alias).ratio()
            if ratio > highest_ratio:
                highest_ratio = ratio
                best_match = key
    
    return best_match if highest_ratio > 0.4 else None


async def _fetch_english_joke(category: str = None):
    """Fetch a joke from jokeapi.dev for English users"""
    base_url = "https://v2.jokeapi.dev/joke/"
    
    # Determine categories to use
    if category:
        category_key = await _get_category(category, ENGLISH_CATEGORY_MAP)
        if category_key:
            categories = category_key
        else:
            categories = "Any"
    else:
        categories = "Any"
    
    url = f"{base_url}{categories}?blacklistFlags=nsfw,explicit&type=single,twopart"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if not data.get('error'):
                        # Handle two-part jokes
                        if data['type'] == 'twopart':
                            return {
                                'joke': data['delivery'],
                                'setup': data['setup'],
                                'category': data['category']
                            }
                        # Handle single jokes
                        else:
                            return {
                                'joke': data['joke'],
                                'setup': None,
                                'category': data['category']
                            }
    except Exception:
        pass
    
    return None


async def _fetch_french_joke(category: str = None):
    """Fetch a joke from blagues_api for French users"""
    try:
        # Get joke by category if specified
        blagues = BlaguesAPI(config.get('api-keys')['blagues'])
        
        if category:
            category_key = await _get_category(category, FRENCH_CATEGORY_MAP)
            if category_key:
                blague = await blagues.random_categorized(category_key)
            else:
                blague = await blagues.random()
        else:
            blague = await blagues.random()
        
        # Translate joke type
        joke_type = FRENCH_TYPE_TRANSLATIONS.get(blague.type, blague.type)
        
        return {
            'joke': blague.joke,
            'answer': blague.answer,
            'type': joke_type
        }
    except Exception:
        return None


def _create_joke_embed(lang: str, joke_data: dict):
    """Create an embed for displaying a joke"""
    if lang.startswith("en"):
        # English joke embed
        if joke_data['setup']:
            # Two-part joke
            embed = nextcord.Embed(
                title=text('joke_title', lang),
                description=joke_data['setup'],
                color=config.get('embed-color')
            )
            embed.add_field(name="** **", value=f"||{joke_data['joke']}||", inline=False)
        else:
            # Single joke
            embed = nextcord.Embed(
                title=text('joke_title', lang),
                description=joke_data['joke'],
                color=config.get('embed-color')
            )
        
        embed.set_footer(text=f"{text('joke_category', lang)}: {joke_data['category']}")
    else:
        # French joke embed
        embed = nextcord.Embed(
            title=text('joke_title', lang),
            description=joke_data['joke'],
            color=config.get('embed-color')
        )
        embed.add_field(name="** **", value=f"||{joke_data['answer']}||", inline=False)
        embed.set_footer(text=f"{text('joke_type', lang)}: {joke_data['type']}")
    
    return embed


async def _joke(lang: str,category: str = None):
    """Main joke function that handles both English and French jokes"""
    if lang.startswith("en"):
        joke_data = await _fetch_english_joke(category)
        if not joke_data:
            return None
    else:
        joke_data = await _fetch_french_joke(category)
        if not joke_data:
            return None
    
    return _create_joke_embed(lang, joke_data)


async def joke_text(lang: str, message: nextcord.Message):
    """Handle text command for jokes"""
    # Normalize the category from message content
    category = message.content.lower().replace(
        " ", "").replace(
        "pp", "p").replace( # misspellings
        "mm", "m").replace( # misspellings
        "é", "e").replace(
        "è", "e").replace(
        "ê", "e") if message.content else None
    
    embed = await _joke(lang, category)
    
    if embed:
        await message.reply(embed=embed, mention_author=False)
    else:
        await message.reply(text('joke_error', lang), mention_author=False)

async def joke_slash(lang: str, interaction: nextcord.Interaction, category: str = None):
    """Handle slash command for jokes"""
    embed = await _joke(lang, category)
    
    if embed:
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(text('joke_error', lang), ephemeral=True)


info = {
    "joke": {
        "category": "fun",
        "aliases": ["blague", "j"],
        "hidden_aliases": ["jokes", "blagues"],
        "available": ["slash_command", "text_command"],
        "visibility": "everyone",
        "user_permissions": [],
        "name": "joke_name",
        "desc": "joke_desc",
        "args": [
            {
                "name": "joke_arg_name",
                "desc": "joke_arg_desc",
                "required": False,
                "autocomplete": True
            }
        ]
    }
}

cmd = CmdLocale(list(info.keys())[0], get_commands_locales(info))

class JokeCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    async def category_autocomplete(self, interaction: nextcord.Interaction, current: str):
        """Provide autocomplete suggestions based on user's language"""
        user_lang = get_lang(interaction)
        
        # Select categories based on language
        if user_lang.startswith("en"):
            categories = ENGLISH_CATEGORIES
        else:
            categories = FRENCH_CATEGORIES
        
        # Filter categories based on current input
        if current:
            filtered = {key: value for key, value in categories.items()
                        if current.lower() in key.lower() or current.lower() in value.lower()}
            return filtered
        
        return categories
    
    @check_ban()
    @application_checks.has_permissions(**{perm: True for perm in cmd.user_permissions})
    @slash_command(
        name=cmd.name,
        description=cmd.description,
        name_localizations=cmd.name_localizations,
        description_localizations=cmd.description_localizations
    )
    async def joke_command(self, interaction: nextcord.Interaction,
        category: str = get_slash_option(cmd.arg(0))
    ):
        await joke_slash(get_lang(interaction), interaction, category)
    
    @joke_command.on_autocomplete("category")
    async def on_category_autocomplete(self, interaction: nextcord.Interaction, category: str):
        await interaction.response.send_autocomplete(await self.category_autocomplete(interaction, category))


def setup(bot: commands.Bot):
    bot.add_cog(JokeCog(bot))

# Text command handler wrapper that adapts to message handler signature
async def _message_handler(bot, message: nextcord.Message, lang: str, prefix: str):
    await joke_text(lang, message)
