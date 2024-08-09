import nextcord

from utils.get_commands_locales import get_commands_locales
from utils.languages import text
from utils.settings import prefix
from utils.settings import lang as language

from commands.roll import roll_dice
from commands.settings.set_prefix import set_prefix
from commands.settings.set_guild_lang import set_guild_lang


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
    
    for prefix in sorted_prefixes:
        if content.lower().startswith(prefix):
            return content[len(prefix):].strip()
    return content.strip()


commands = get_commands_locales()

async def handle_message(bot, message: nextcord.Message):
    p = prefix.get(message.guild.id)
    
    if message.author == bot.user:
        return
    
    # Check if the message mentions the bot
    bot_mention = f'<@{bot.user.id}>'
    if message.content == bot_mention or (bot_mention in message.content.lstrip('!') and not message.content.startswith(bot_mention)):
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
        
        for command_name, command_data in commands.items():
            command_aliases = [command_name, *command_data.get('aliases', []), *command_data.get('hidden_aliases', [])]
            if command in command_aliases:
                message.content = remove_command(message.content, command_aliases)
                print('msg: ', message.content)
                
                if command_name == 'prefix':
                    await set_prefix(lang, message)
                elif command_name == 'lang':
                    await set_guild_lang(lang, message)
                elif command_name == 'roll':
                    await roll_dice(lang, p, message)
                
                break
        else:
            print(f"Unknown command: {command}")
