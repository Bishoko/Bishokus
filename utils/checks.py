import inspect
from functools import wraps
import nextcord
from nextcord.ext import application_checks
from utils.languages import text
from utils.settings.lang import get_lang
from utils.settings.lang import get as get_lang_text_command

from utils.vip import vip_command as vip_only
from utils.config import config

OWNER_ID = config["owner-id"]


def _find_message(args, kwargs):
    message = kwargs.get('message')
    if message is None:
        for arg in args:
            if isinstance(arg, nextcord.Message):
                return arg
    return message


def _command_check_wrapper(func, slash_predicate_factory=None, text_handler_factory=None):
    # Route the decorator logic based on whether the command uses interaction or message.
    sig = inspect.signature(func)
    params = list(sig.parameters.keys())

    if 'interaction' in params and slash_predicate_factory is not None:
        return application_checks.check(slash_predicate_factory())(func)

    if 'message' in params and text_handler_factory is not None:
        text_handler = text_handler_factory()

        @wraps(func)
        async def wrapper(*args, **kwargs):
            message = _find_message(args, kwargs)
            if message is None:
                return await func(*args, **kwargs)

            should_continue = await text_handler(message)
            if not should_continue:
                return

            return await func(*args, **kwargs)

        return wrapper

    return func


def guild_only():
    """
    A decorator that ensures the command is happening in a guild (DMs not allowed).

    Works with both slash commands (interaction) and text commands (message).
    
    For slash commands:
        @checks.guild_only()
        async def some_command(interaction: nextcord.Interaction):
            # Command implementation
    
    For text commands:
        @checks.guild_only()
        async def some_command(bot, message: nextcord.Message, lang: str, prefix_str: str):
            # Command implementation
    """
    def decorator(func):
        def slash_predicate_factory():
            async def predicate(interaction: nextcord.Interaction):
                if interaction.guild is None:
                    await interaction.response.send_message(
                        text('guild_only_error', get_lang(interaction)),
                        ephemeral=True
                    )
                    return False
                return True

            return predicate

        def text_handler_factory():
            async def handler(message: nextcord.Message):
                if message.guild is None:
                    await message.reply(
                        text('guild_only_error', get_lang_text_command(
                            message.guild.id if message.guild else 0,
                            message.author.id
                        )),
                        mention_author=False
                    )
                    return False
                return True

            return handler

        return _command_check_wrapper(func, slash_predicate_factory, text_handler_factory)
    
    return decorator


def owner_only():
    """
    A decorator that ensures the command is only executed by the bot owner.

    Works with both slash commands (interaction) and text commands (message).
    
    For slash commands:
        @checks.owner_only()
        async def some_command(interaction: nextcord.Interaction):
            # Command implementation
    
    For text commands:
        @checks.owner_only()
        async def some_command(bot, message: nextcord.Message, lang: str, prefix_str: str):
            # Command implementation
    """
    def decorator(func):
        def slash_predicate_factory():
            async def predicate(interaction: nextcord.Interaction):
                if interaction.user.id != OWNER_ID:
                    await interaction.response.send_message(
                        text('owner_only_error', get_lang(interaction))
                    )
                    return False
                return True

            return predicate

        def text_handler_factory():
            async def handler(message: nextcord.Message):
                if message.author.id != OWNER_ID:
                    return False
                return True

            return handler

        return _command_check_wrapper(func, slash_predicate_factory, text_handler_factory)
    
    return decorator


def bot_permissions(**perms: bool):
    """
    A decorator that ensures the bot has the specified permissions to execute the command.

    Works with both slash commands (interaction) and text commands (message).
    
    For slash commands:
        @checks.bot_permissions(manage_guild=True)
        async def some_command(interaction: nextcord.Interaction):
            # Command implementation
    
    For text commands:
        @checks.bot_permissions(manage_guild=True)
        async def some_command(bot, message: nextcord.Message, lang: str, prefix_str: str):
            # Command implementation
    """
    def decorator(func):
        def _check_permissions(permissions, lang):
            missing = [text("perm_" + perm, lang) for perm, value in perms.items() if getattr(permissions, perm) != value]
            
            if len(missing) == 1:
                reply = text('bot_missing_permission', lang).replace("%permissions%", f"`{missing[0]}`")
            else:
                missing_list = ", ".join(f"`{perm}`" for perm in missing)
                reply = text('bot_missing_permissions', lang).replace("%permissions%", missing_list)
            
            return missing, reply
        
        def slash_predicate_factory():
            async def predicate(interaction: nextcord.Interaction):
                lang = get_lang(interaction)
                permissions = interaction.guild.me.guild_permissions
                missing, reply = _check_permissions(permissions, lang)

                if not missing:
                    return True

                await interaction.response.send_message(reply, ephemeral=True)
                return False

            return predicate

        def text_handler_factory():
            async def handler(message: nextcord.Message):
                lang = get_lang_text_command(
                    message.guild.id if message.guild else 0,
                    message.author.id
                )
                permissions = message.guild.me.guild_permissions
                missing, reply = _check_permissions(permissions, lang)

                if not missing:
                    return True

                await message.reply(reply, mention_author=False)
                return False

            return handler

        return _command_check_wrapper(func, slash_predicate_factory, text_handler_factory)
    
    return decorator


def user_permissions(**perms: bool):
    """
    A decorator that ensures the command is executed by a user with the specified permissions.

    Works with both slash commands (interaction) and text commands (message).
    
    For slash commands:
        @checks.user_permissions(manage_guild=True)
        async def some_command(interaction: nextcord.Interaction):
            # Command implementation
    
    For text commands:
        @checks.user_permissions(manage_guild=True)
        async def some_command(bot, message: nextcord.Message, lang: str, prefix_str: str):
            # Command implementation
    """
    def decorator(func):
        def _check_permissions(permissions, lang):
            missing = [text("perm_" + perm, lang) for perm, value in perms.items() if getattr(permissions, perm) != value]
            
            if len(missing) == 1:
                reply = text('user_missing_permission', lang).replace("%permissions%", f"`{missing[0]}`")
            else:
                missing_list = ", ".join(f"`{perm}`" for perm in missing)
                reply = text('user_missing_permissions', lang).replace("%permissions%", missing_list)
            
            return missing, reply
        
        def slash_predicate_factory():
            async def predicate(interaction: nextcord.Interaction):
                lang = get_lang(interaction)
                permissions = interaction.user.guild_permissions
                missing, reply = _check_permissions(permissions, lang)

                if not missing:
                    return True

                await interaction.response.send_message(reply, ephemeral=True)
                return False

            return predicate

        def text_handler_factory():
            async def handler(message: nextcord.Message):
                lang = get_lang_text_command(
                    message.guild.id if message.guild else 0,
                    message.author.id
                )
                permissions = message.author.guild_permissions
                missing, reply = _check_permissions(permissions, lang)

                if not missing:
                    return True

                await message.reply(reply, mention_author=False)
                return False

            return handler

        return _command_check_wrapper(func, slash_predicate_factory, text_handler_factory)
    
    return decorator
