import json
import nextcord
from nextcord.ext import commands

from utils.languages import init as langs_init
import utils.sql as db

langs_init()
db.init()

from handlers.message_handler import handle_message
from handlers.slash_commands import register_slash_commands


intents = nextcord.Intents.all()
intents.typing = False
intents.presences = False

def load_config():
    with open("config/config.json", "r") as f:
        return json.load(f)

config = load_config()


bot = commands.Bot(
    owner_id=config.get('owner-id'),
    command_prefix=config['default-prefix'],
    intents=intents
)

@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')


@bot.event
async def on_message(message):
    await handle_message(bot, message)

register_slash_commands(bot)


@bot.event
async def on_application_command_error(interaction: nextcord.Interaction, error: Exception):
    # This function is used to ignore errors that occur when preventing commands for banned users or guilds

    if not isinstance(
        error,
        (
            nextcord.errors.ApplicationCheckFailure,
            nextcord.errors.InteractionResponded,
        ),
    ):
        # Handle other types of errors or re-raise them
        raise error


if config.get('production', False) == True:
    bot.run(config['tokens']['main'])
else:
    bot.run(config['tokens']['test'])