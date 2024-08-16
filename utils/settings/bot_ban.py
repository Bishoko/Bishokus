import mysql.connector
import nextcord
from nextcord.ext import application_checks

import utils.settings.lang as lang
from utils.settings.lang import get_lang
from utils.languages import text
from utils.sql import get_db_connection
from utils.sql.create_guild import guild_db
from utils.sql.create_user import user_db

import json

with open('config/config.json', encoding='utf-8') as config_file:
    config = json.load(config_file)
    default_user_ban_type = config['default-user-ban-type']
    default_guild_ban_type = config['default-guild-ban-type']


@user_db
def ban_user(user_id: int, ban_type: str, reason: str):
    """
    Bans a user from using the bot by setting the bot_banned flag to True in the database.

    Args:
        user_id (int): The ID of the user to ban.
        ban_type (str): The type of ban.
        reason (str): The reason for the ban.

    Raises:
        mysql.connector.Error: If there's an error while updating the database.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        query = '''
        UPDATE users
        SET bot_banned = TRUE,
            bot_banned_type = %s,
            bot_banned_reason = %s,
            bot_banned_history = JSON_ARRAY_APPEND(
                COALESCE(bot_banned_history, JSON_ARRAY()),
                '$',
                JSON_OBJECT('type', %s, 'reason', %s, 'timestamp', CURRENT_TIMESTAMP, 'removed_timestamp', NULL)
            )
        WHERE id = %s
        '''
        cursor.execute(query, (ban_type, reason, ban_type, reason, user_id))
        conn.commit()
    except mysql.connector.Error as err:
        print(f'Error: {err}')
        conn.rollback()
    finally:
        cursor.close()
        conn.close()


@guild_db
def ban_guild(guild_id: int, ban_type: str, reason: str):
    """
    Bans a guild from using the bot by setting the bot_banned flag to True in the database.

    Args:
        guild_id (int): The ID of the guild to ban.
        ban_type (str): The type of ban.
        reason (str): The reason for the ban.

    Raises:
        mysql.connector.Error: If there's an error while updating the database.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        query = '''
        UPDATE guilds
        SET bot_banned = TRUE,
            bot_banned_type = %s,
            bot_banned_reason = %s,
            bot_banned_history = JSON_ARRAY_APPEND(
                COALESCE(bot_banned_history, JSON_ARRAY()),
                '$',
                JSON_OBJECT('type', %s, 'reason', %s, 'timestamp', CURRENT_TIMESTAMP, 'removed_timestamp', NULL)
            )
        WHERE id = %s
        '''
        cursor.execute(query, (ban_type, reason, ban_type, reason, guild_id))
        conn.commit()
    except mysql.connector.Error as err:
        print(f'Error: {err}')
        conn.rollback()
    finally:
        cursor.close()
        conn.close()


@user_db
def unban_user(user_id: int):
    """
    Unbans a user from using the bot by setting the bot_banned flag to False in the database.

    Args:
        user_id (int): The ID of the user to unban.

    Raises:
        mysql.connector.Error: If there's an error while updating the database.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:

        query = '''
        UPDATE users
        SET bot_banned = FALSE,
            bot_banned_type = NULL,
            bot_banned_reason = NULL,
            bot_banned_history = JSON_ARRAY_APPEND(
                bot_banned_history,
                '$[last]',
                JSON_OBJECT('removed_timestamp', CURRENT_TIMESTAMP)
            )
        WHERE id = %s
        '''
        cursor.execute(query, (user_id,))
        conn.commit()
    except mysql.connector.Error as err:
        print(f'Error: {err}')
        conn.rollback()
    finally:
        cursor.close()
        conn.close()


@guild_db
def unban_guild(guild_id: int):
    """
    Unbans a guild from using the bot by setting the bot_banned flag to False in the database.

    Args:
        guild_id (int): The ID of the guild to unban.

    Raises:
        mysql.connector.Error: If there's an error while updating the database.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:

        query = '''
        UPDATE guilds
        SET bot_banned = FALSE,
            bot_banned_type = NULL,
            bot_banned_reason = NULL,
            bot_banned_history = JSON_ARRAY_APPEND(
                bot_banned_history,
                '$[last]',
                JSON_OBJECT('removed_timestamp', CURRENT_TIMESTAMP)
            )
        WHERE id = %s
        '''
        cursor.execute(query, (guild_id,))
        conn.commit()
    except mysql.connector.Error as err:
        print(f'Error: {err}')
        conn.rollback()
    finally:
        cursor.close()
        conn.close()


@user_db
@guild_db
def is_banned(id: int, is_guild: bool = False) -> bool:
    """
    Checks whether a user or guild is banned from using the bot.
    
    Args:
        id (int): The ID of the user or guild to check.
        is_guild (bool): True if checking a guild, False if checking a user.

    Returns:
        bool: True if the entity is banned, False otherwise.

    Raises:
        mysql.connector.Error: If there's an error while querying the database.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        table = 'guilds' if is_guild else 'users'
        query = f'SELECT bot_banned FROM {table} WHERE id = %s'
        cursor.execute(query, (id,))
        result = cursor.fetchone()
        
        return result[0] if result else False
    except mysql.connector.Error as err:
        print(f'Error: {err}')
        return False
    finally:
        cursor.close()
        conn.close()


@user_db
@guild_db
def get_ban_reason(id: int, is_guild: bool = False) -> str:
    """
    Gets the ban reason for a user or guild.

    Args:
        id (int): The ID of the user or guild to check.
        is_guild (bool): True if checking a guild, False if checking a user.

    Returns:
        str: The ban reason if the entity is banned, None otherwise.

    Raises:
        mysql.connector.Error: If there's an error while querying the database.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        table = 'guilds' if is_guild else 'users'
        query = f'SELECT bot_banned_reason FROM {table} WHERE id = %s AND bot_banned = TRUE'
        cursor.execute(query, (id,))
        result = cursor.fetchone()
        
        return result[0] if result else None
    except mysql.connector.Error as err:
        print(f'Error: {err}')
        return None
    finally:
        cursor.close()
        conn.close()


@user_db
@guild_db
def get_ban_type(id: int, is_guild: bool = False) -> str:
    """
    Gets the ban type for a user or guild.

    Args:
        id (int): The ID of the user or guild to check.
        is_guild (bool): True if checking a guild, False if checking a user.

    Returns:
        str: The ban type if the entity is banned, None otherwise.

    Raises:
        mysql.connector.Error: If there's an error while querying the database.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        table = 'guilds' if is_guild else 'users'
        query = f'SELECT bot_banned_type FROM {table} WHERE id = %s AND bot_banned = TRUE'
        cursor.execute(query, (id,))
        result = cursor.fetchone()
        
        default = default_guild_ban_type if is_guild else default_user_ban_type
        if result and result[0]:
            result = result[0].lower()
            if result == 'default':
                result = default
        else:
            result = default
            
        return result

    except mysql.connector.Error as err:
        print(f'Error: {err}')
        return None
    finally:
        cursor.close()
        conn.close()


@user_db
@guild_db
async def check_ban_on_message(message: nextcord.Message):
    """
    A function that checks if a user or guild is banned from using the bot for on_message events.

    This function checks whether the user sending the message or the guild where the message
    is sent is banned from using the bot.

    Args:
        message: The message object from the on_message event.

    Returns:
        bool: True if the user and guild are not banned, False otherwise.

    Usage:
        @bot.event
        async def on_message(message):
            if not check_ban_on_message(message):
                return
            # Rest of the on_message logic
    """
    user_banned = is_banned(message.author.id)
    guild_banned = is_banned(message.guild.id, is_guild=True) if message.guild else False

    if user_banned:
        ban_type = get_ban_type(message.author.id)
        if ban_type == 'banned_message':
            await message.channel.send(
                text('user_is_bot_banned',
                    lang.get(message.guild.id, message.author.id)).replace('%ban_reason%', str(get_ban_reason(message.author.id))
                )
            )
        return False
    
    if guild_banned:
        ban_type = get_ban_type(message.guild.id, is_guild=True)
        if ban_type == 'banned_message':
            await message.channel.send(
                text('guild_is_bot_banned',
                    lang.get(message.guild.id, message.author.id)).replace('%ban_reason%', str(get_ban_reason(message.guild.id, is_guild=True))
                )
            )
        elif ban_type == 'instant_leave':
            await message.guild.leave()
        
        return False
    
    return True


def check_ban():
    """
    A decorator that checks if a user or guild is banned from using the bot.

    This function returns a predicate that can be used as a check for Discord interactions.
    It verifies whether the user initiating the interaction or the guild where the interaction
    is taking place is banned from using the bot.

    Returns:
        function: A predicate function that can be used as a check for Discord interactions.

    Usage:
        @check_ban()
        async def some_command(interaction: nextcord.Interaction):
            # Command implementation
    """

    async def predicate(interaction: nextcord.Interaction):
        user_banned = is_banned(interaction.user.id)
        guild_banned = is_banned(interaction.guild_id, is_guild=True) if interaction.guild else False

        if user_banned:
            ban_type = get_ban_type(interaction.user.id)
            if ban_type == 'banned_message':
                await interaction.response.send_message(
                    text('user_is_bot_banned',
                        get_lang(interaction)).replace('%ban_reason%', str(get_ban_reason(interaction.user.id))
                    ),
                    ephemeral=True
                )
            return False
        
        if guild_banned:
            ban_type = get_ban_type(interaction.guild_id, is_guild=True)
            if ban_type == 'banned_message':
                await interaction.response.send_message(
                    text('guild_is_bot_banned',
                        get_lang(interaction)).replace('%ban_reason%', str(get_ban_reason(interaction.guild_id, is_guild=True))
                    ),
                    ephemeral=True
                )
            elif ban_type == 'instant_leave':
                await interaction.guild.leave()
                
            return False
        
        return True

    return application_checks.check(predicate)