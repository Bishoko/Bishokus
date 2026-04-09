import os
import json
import nextcord
from nextcord.ext import commands, tasks

import utils.global_variables as gv
from utils.languages import init as langs_init
from utils.logger import log
import utils.sql as db

langs_init()
db.init()

from handlers.message_handler import handle_message
from handlers.on_guild_join import handle_guild_join
from handlers.on_guild_remove import handle_guild_remove


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



@tasks.loop(seconds=45)
async def status_loop():
    """Cycle through bot status messages."""
    if bot.latency == 0:
        return
    
    statuses = [
        nextcord.Activity(
            type=nextcord.ActivityType.watching,
            name="!help | !invite"
        ),
        nextcord.Activity(
            type=nextcord.ActivityType.watching,
            name=f"{len(bot.guilds)} servers!"
        ),
    ]
    
    current_status = statuses[status_loop.current_index % len(statuses)]
    await bot.change_presence(activity=current_status)
    
    status_loop.current_index = (status_loop.current_index + 1) % len(statuses)


@bot.event
async def on_ready():
    log.info(f'{bot.user.name} has connected to Discord!')
    
    status_loop.current_index = 0
    status_loop.start()


@bot.event
async def on_message(message):
    await handle_message(bot, message)


@bot.event
async def on_guild_join(guild):
    await handle_guild_join(bot, guild)

@bot.event
async def on_guild_remove(guild):
    await handle_guild_remove(bot, guild)


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
        log.exception(error)
        raise error


# Load cogs from the commands directory
commands_info = {}
message_handlers = {}
for root, dirs, files in os.walk('commands'):
    prioritized_files = sorted(files, key=lambda filename: (not filename.startswith('_'), filename.lower()))
    for filename in prioritized_files:
        if filename.endswith('.py') and filename not in ['__init__.py', 'template.py']:
            log.info(f"Processing file: {filename}")
            module_path = os.path.join(root, filename)[:-3].replace(os.sep, '.')
            bot.load_extension(module_path)
            
            module = __import__(module_path, fromlist=['info', '_message_handler'])
            info = getattr(module, 'info', None)
            message_handler = getattr(module, '_message_handler', None)
            message_handler_multiple = getattr(module, '_message_handlers', None)
            
            if info:
                command_name = list(info.keys())[0]
                log.info(f"Loaded command: {command_name} ({module_path})")
                commands_info = {**commands_info, **info}
                gv.set("commands_info", commands_info)
                
                # Store the message handler function if available
                for command_name, command in info.items():
                    if message_handler and "text_command" in command["available"]:
                        message_handlers[command_name] = message_handler
                        log.info(f"  Registered text command handler for: {command_name}")
                    if message_handler_multiple and "text_command" in command["available"]:
                        for handler_name, handler_func in message_handler_multiple.items():
                            if handler_name == command_name:
                                message_handlers[command_name] = handler_func
                                log.info(f"  Registered text command handler for: {command_name}")
            
# Store message handlers in global variables
gv.set("message_handlers", message_handlers)
log.success("All cogs loaded successfully.")


if config.get('production', False) == True:
    bot.run(config['tokens']['main'])
else:
    bot.run(config['tokens']['test'])