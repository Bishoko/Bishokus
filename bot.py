import os
import json
import nextcord
from nextcord.ext import commands

import utils.global_variables as gv
from utils.languages import init as langs_init
from utils.settings.bot_ban import get_ban_type
import utils.sql as db

langs_init()
db.init()

from handlers.message_handler import handle_message


intents = nextcord.Intents.all()
intents.typing = False
intents.presences = False

def load_config():
    with open("config/config.json", "r", encoding='utf-8') as f:
        return json.load(f)

config = load_config()


bot = commands.Bot(
    owner_id=config.get('owner-id'),
    command_prefix=config['default-prefix'],
    intents=intents
)
gv.set('bot', bot)
gv.set('client', bot)


@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')


@bot.event
async def on_message(message):
    await handle_message(bot, message)


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


@bot.event
async def on_guild_join(guild):
    if get_ban_type(guild.id, is_guild=True) == 'instant_leave':
        await guild.leave()
        print(f"Left banned guild: {guild.name} (ID: {guild.id})")


# Load cogs from the commands directory
commands_info = {}
message_handlers = {}
for root, dirs, files in os.walk('commands'):
    prioritized_files = sorted(files, key=lambda filename: (not filename.startswith('_'), filename.lower()))
    for filename in prioritized_files:
        if filename.endswith('.py') and filename not in ['__init__.py', 'template.py']:
            print(f"Processing file: {filename}")
            module_path = os.path.join(root, filename)[:-3].replace(os.sep, '.')
            bot.load_extension(module_path)
            
            module = __import__(module_path, fromlist=['info', '_message_handler'])
            info = getattr(module, 'info', None)
            message_handler = getattr(module, '_message_handler', None)
            
            if info:
                command_name = list(info.keys())[0]
                print(f"Loaded command: {command_name} ({module_path})")
                commands_info = {**commands_info, **info}
                gv.set("commands_info", commands_info)
                
                # Store the message handler function if available
                for command_name, command in info.items():
                    if message_handler and "text_command" in command["available"]:
                        message_handlers[command_name] = message_handler
                        print(f"  Registered text command handler for: {command_name}")
            
# Store message handlers in global variables
gv.set("message_handlers", message_handlers)
                
print("All cogs loaded successfully.")


if config.get('production', False) == True:
    bot.run(config['tokens']['main'])
else:
    bot.run(config['tokens']['test'])