import nextcord
import time

from utils.get_commands_locales import get_commands_locales
from utils.languages import text
from utils.settings import prefix
from utils.settings import lang as language
from utils.settings.bot_ban import check_ban_on_message
import utils.global_variables as gv

def remove_command(content: str, prefixes: list) -> str:
    """
    Remove command prefix from the content string.

    Args:
        content (str): The input string containing the command.
        prefixes (list): A list of possible command prefixes.

    Returns:
        str: The content string with the command prefix removed, if found.

    Note:
        Prefixes are sorted by length in descending order to ensure longer prefixes
        are checked first. This prevents shorter prefixes from being removed prematurely.
        For example, if content='rolldice' and both 'roll' and 'r' are prefixes,
        we want to check 'roll' before 'r' to avoid incorrectly removing just 'r'.
    """
    sorted_prefixes = sorted(prefixes, key=len, reverse=True)
    
    for prefix_item in sorted_prefixes:
        if content.lower().startswith(prefix_item):
            return content[len(prefix_item):].strip()
    return content.strip()


async def handle_message(bot, message: nextcord.Message):
    p = prefix.get(message.guild.id)
    
    if message.author == bot.user:
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
    
    
    if message.content.startswith(p) or message.content.lstrip('!').startswith(f'<@{bot.application_id}>'):
        message.content = message.content.removeprefix(p).removeprefix(f'<@{bot.application_id}>').removeprefix(f'<@!{bot.application_id}>').strip()        
        if not len(message.content) > 0:
            return
        command = message.content.split()[0].lower()
        
        lang = language.get(message.guild.id, message.author.id)
        
        # Get commands info and message handlers from global variables
        commands_info = gv.get("commands_info")
        message_handlers = gv.get("message_handlers") or {}
        
        if commands_info is None:
            commands_info = get_commands_locales()
            print(f"Loaded commands locales")
        
        for command_name, command_data in commands_info.items():
            command_aliases = [command_name, *command_data.get('aliases', []), *command_data.get('hidden_aliases', [])]
            if command in command_aliases:
                if not await check_ban_on_message(message):
                    return
                
                message.content = remove_command(message.content, command_aliases)
                
                # Check if there's a text command handler for this command
                if command_name in message_handlers:
                    handler = message_handlers[command_name]
                    # Call the handler with standardized signature
                    await handler(bot, message, lang, p)
                else:
                    print(f"No text command handler found for: {command_name}")
                
                break
        else:
            print(f"Unknown command: {command}")
