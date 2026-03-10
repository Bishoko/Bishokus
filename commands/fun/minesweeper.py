import nextcord
from nextcord.ext import commands, application_checks
from nextcord.application_command import slash_command
from utils.get_commands_locales import get_commands_locales
from utils.locale_helpers import CmdLocale, get_slash_option
from utils import config
from utils.settings.bot_ban import check_ban
from utils.languages import text
from utils.settings import prefix
from utils.settings.lang import get_lang

import random


# Default: 8x8 with 10 bombs
DEFAULT_GRID = (8, 8, 10, None)

def _generate_minesweeper_grid(columns: int, rows: int, bombs: int) -> tuple[list, float]:
    """Generate minesweeper grid and calculate bomb percentage."""
    # Create grid filled with zeros
    grid = [[0 for _ in range(columns)] for _ in range(rows)]

    # Place bombs randomly
    bombs_placed = 0
    while bombs_placed < bombs:
        x = random.randint(0, columns - 1)
        y = random.randint(0, rows - 1)
        if grid[y][x] != 'B':
            grid[y][x] = 'B'
            bombs_placed += 1

    # Calculate adjacent bombs for each cell
    for pos_y in range(rows):
        for pos_x in range(columns):
            if grid[pos_y][pos_x] != 'B':
                adjacent_bomb_count = 0
                for adj_y, adj_x in [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (-1, 1), (1, -1), (-1, -1)]:
                    try:
                        if grid[adj_y + pos_y][adj_x + pos_x] == 'B':
                            adjacent_bomb_count += 1
                    except IndexError:
                        pass
                grid[pos_y][pos_x] = adjacent_bomb_count

    # Calculate bomb percentage
    percentage = (bombs / (columns * rows)) * 100
    percentage = round(percentage, 2)

    return grid, percentage


def _format_grid_as_string(grid: list) -> str:
    """Convert grid to Discord-formatted string with spoiler tags and emojis."""
    emoji_map = {
        '0': '||:zero:||',
        '1': '||:one:||',
        '2': '||:two:||',
        '3': '||:three:||',
        '4': '||:four:||',
        '5': '||:five:||',
        '6': '||:six:||',
        '7': '||:seven:||',
        '8': '||:eight:||',
        'B': '||:boom:||'
    }

    result = []
    for row in grid:
        row_str = ''.join(str(cell) for cell in row)
        for digit, emoji in emoji_map.items():
            row_str = row_str.replace(digit, emoji)
        result.append(row_str)

    return '\n'.join(result)


def _parse_minesweeper_args(content: str) -> tuple[int, int, int, str]:
    """Parse minesweeper arguments and return columns, rows, bombs, and error message if any."""
    args = content.strip().split() if content.strip() else []

    if not args:
        return DEFAULT_GRID

    try:
        args = [int(arg) for arg in args]
    except ValueError:
        return None, None, None, "invalid_args"

    if len(args) == 1:
        # One argument: square grid with bomb count = size * 1.25
        size = args[0]
        return size, size, int(size * 1.25), None
    elif len(args) == 2:
        # Two arguments: columns, rows with bomb count = columns * 1.25
        columns, rows = args[0], args[1]
        return columns, rows, int(columns * 1.25), None
    elif len(args) == 3:
        # Three arguments: columns, rows, bombs
        columns, rows, bombs = args[0], args[1], args[2]
        return columns, rows, bombs, None
    else:
        return None, None, None, "invalid_format"


def _validate_minesweeper_params(columns: int, rows: int, bombs: int, lang: str) -> str:
    """Validate minesweeper parameters and return error message if invalid."""
    if columns > 11 or rows > 11:
        return text('minesweeper_size_limit_error', lang)

    if columns < 1 or rows < 1 or bombs < 1:
        return text('minesweeper_negative_error', lang)

    if bombs >= columns * rows:
        return text('minesweeper_too_many_bombs_error', lang)

    return None


async def _minesweeper(lang: str, prefix: str, interaction_or_message, columns: int = None, rows: int = None, bombs: int = None):
    """Generate and send minesweeper game."""
    is_interaction = isinstance(interaction_or_message, nextcord.Interaction)
    
    columns = int(columns) if isinstance(columns, int) else DEFAULT_GRID[0]
    rows = int(rows) if isinstance(rows, int) else DEFAULT_GRID[1]
    bombs = int(bombs) if isinstance(bombs, int) else DEFAULT_GRID[2]

    # Parse arguments if strings provided
    if isinstance(columns, str):
        parsed = _parse_minesweeper_args(columns)
        if parsed[-1]:  # Error message
            error_msg = text(f'minesweeper_{parsed[-1]}', lang).replace('%prefix%', prefix)
            if is_interaction:
                await interaction_or_message.response.send_message(error_msg, ephemeral=True)
            else:
                await interaction_or_message.channel.send(error_msg)
            return
        columns, rows, bombs = parsed[0], parsed[1], parsed[2]

    # Validate parameters
    validation_error = _validate_minesweeper_params(columns, rows, bombs, lang)
    if validation_error:
        if is_interaction:
            await interaction_or_message.response.send_message(validation_error, ephemeral=True)
        else:
            await interaction_or_message.channel.send(validation_error)
        return

    # Generate grid
    grid, percentage = _generate_minesweeper_grid(columns, rows, bombs)
    grid_str = _format_grid_as_string(grid)

    # Create embed
    embed = nextcord.Embed(
        title='🙂 Minesweeper 😵',
        color=config.get('embed-color')
    )
    embed.add_field(name=text('minesweeper_columns', lang), value=columns, inline=True)
    embed.add_field(name=text('minesweeper_rows', lang), value=rows, inline=True)
    embed.add_field(name=text('minesweeper_total_cells', lang), value=columns * rows, inline=True)
    embed.add_field(name=f'💣 {text("minesweeper_bombs", lang)}', value=bombs, inline=True)
    embed.add_field(name=f'💣 {text("minesweeper_bomb_percentage", lang)}', value=f'{percentage}%', inline=True)
    embed.add_field(name=text('minesweeper_requested_by', lang), value=interaction_or_message.user.display_name if is_interaction else interaction_or_message.author.display_name, inline=True)

    if is_interaction:
        await interaction_or_message.response.send_message(f'\U0000FEFF\n{grid_str}', embed=embed)
    else:
        await interaction_or_message.channel.send(f'\U0000FEFF\n{grid_str}', embed=embed)


async def minesweeper_text(lang: str, prefix: str, message: nextcord.Message):
    await _minesweeper(lang, prefix, message, message.content)

async def minesweeper_slash(lang: str, prefix: str, interaction: nextcord.Interaction, columns: int = None, rows: int = None, bombs: int = None):
    await _minesweeper(lang, prefix, interaction, columns, rows, bombs)


info = {
    "minesweeper": {
        "category": "fun",
        "aliases": ["ms"],
        "hidden_aliases": ["mine", "mines", "saper", "buscaminas", "minesweeper_game", "mineswiper", "demineur"],
        "available": ["slash_command", "text_command"],
        "visibility": "everyone",
        "user_permissions": [],
        "name": "minesweeper_name",
        "desc": "minesweeper_desc",
        "args": [
            {
                "name": "minesweeper_columns_arg_name",
                "desc": "minesweeper_columns_arg_desc",
                "required": False
            },
            {
                "name": "minesweeper_rows_arg_name",
                "desc": "minesweeper_rows_arg_desc",
                "required": False
            },
            {
                "name": "minesweeper_bombs_arg_name",
                "desc": "minesweeper_bombs_arg_desc",
                "required": False
            }
        ]
    }
}

cmd = CmdLocale(list(info.keys())[0], get_commands_locales(info))

class MinesweeperCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @check_ban()
    @slash_command(
        name=cmd.name,
        description=cmd.description,
        name_localizations=cmd.name_localizations,
        description_localizations=cmd.description_localizations
    )
    async def minesweeper_command(self, interaction: nextcord.Interaction,
        columns: int = get_slash_option(cmd.arg(0)),
        rows: int = get_slash_option(cmd.arg(1)),
        bombs: int = get_slash_option(cmd.arg(2))
    ):
        await minesweeper_slash(get_lang(interaction), prefix.get(interaction.guild_id), interaction, columns, rows, bombs)


def setup(bot: commands.Bot):
    bot.add_cog(MinesweeperCog(bot))

# Text command handler wrapper that adapts to message handler signature
async def _message_handler(bot, message: nextcord.Message, lang: str, prefix: str):
    await minesweeper_text(lang, prefix, message)
