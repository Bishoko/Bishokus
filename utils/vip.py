import inspect
import nextcord
from nextcord.ext import application_checks
from functools import wraps
from datetime import datetime
from dateutil import parser

from utils.languages import text
from utils.settings.lang import get_lang
from utils.settings.lang import get as get_lang_text_command
from utils.sql.get import get
from utils.sql import get_db_connection
from utils.logger import log


def add(user_id: int, vip_end: datetime):
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE users SET is_vip = TRUE, vip_end = %s WHERE id = %s",
            (vip_end.strftime('%Y-%m-%d %H:%M:%S'), user_id)
        )
        connection.commit()
        log.info(f"Added VIP for user_id: {user_id}")
    
    finally:
        cursor.close()
        connection.close()

def remove(user_id: int):
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE users SET is_vip = FALSE, vip_end = NULL WHERE id = %s",
            (user_id,)
        )
        connection.commit()
        log.info(f"Removed VIP for user_id: {user_id}")
    
    finally:
        cursor.close()
        connection.close()

def is_vip(user_id: int):
    vip_state = bool(get("is_vip", user_id=user_id))
    if not vip_state:
        return False
    
    vip_end_str = get("vip_end", user_id=user_id)
    if not vip_end_str:
        return False
    
    vip_end: datetime = parser.parse(vip_end_str)
    
    if vip_state and vip_end:
        if vip_end > datetime.now():
            return True
        else:
            remove(user_id)
            return False
    
    return False


def vip_command():
    """
    A decorator that ensures the command is executed by a VIP user.

    Works with both slash commands (interaction) and text commands (message).
    
    For slash commands:
        @vip_command()
        async def some_command(interaction: nextcord.Interaction):
            # Command implementation
    
    For text commands:
        @vip_command()
        async def some_command(bot, message: nextcord.Message, lang: str, prefix_str: str):
            # Command implementation
    """
    def decorator(func):
        # Check the function signature to determine if it's a slash or text command
        sig = inspect.signature(func)
        params = list(sig.parameters.keys())
        
        # For slash commands (and subcommands), use application_checks.check
        if 'interaction' in params:
            async def predicate(interaction: nextcord.Interaction):
                if not is_vip(interaction.user.id):
                    await interaction.response.send_message(
                        text('vip_only_error', get_lang(interaction)),
                        ephemeral=True
                    )
                    return False
                return True
            
            return application_checks.check(predicate)(func)
        
        # For text commands, use a regular wrapper
        elif 'message' in params:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Find the message object in args or kwargs
                message = kwargs.get('message')
                if message is None:
                    # Check args - message can be at different positions
                    for arg in args:
                        if isinstance(arg, nextcord.Message):
                            message = arg
                            break
                
                if not is_vip(message.author.id):
                    await message.reply(
                        text('vip_only_error', get_lang_text_command(
                                message.guild.id if message.guild else 0,
                                message.author.id
                            )
                        ),
                        mention_author=False
                    )
                    return
                
                return await func(*args, **kwargs)
            
            return wrapper
        
        else:
            # Fallback: just return the function as is
            return func
    
    return decorator