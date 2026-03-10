import inspect
from functools import wraps
import nextcord
from nextcord.ext import application_checks
from utils.languages import text
from utils.settings.lang import get_lang
from utils.settings.lang import get as get_lang_text_command


def guild_only():
    """
    A decorator that ensures the command is happening in a guild (DMs not allowed).

    Works with both slash commands (interaction) and text commands (message).
    
    For slash commands:
        @guild_only()
        async def some_command(interaction: nextcord.Interaction):
            # Command implementation
    
    For text commands:
        @guild_only()
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
                if interaction.guild is None:
                    await interaction.response.send_message(
                        text('guild_only_error', get_lang(interaction)),
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
                
                if message and message.guild is None:
                    await message.reply(
                        text('guild_only_error', get_lang_text_command(
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