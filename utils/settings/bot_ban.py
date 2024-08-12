import nextcord
from nextcord.ext import application_checks

import mysql.connector
from utils.sql import get_db_connection
from utils.sql.create_guild import guild_db
from utils.sql.create_user import user_db


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
@guild_db
def is_banned(id: int, is_guild: bool = False) -> bool:
    """
    Checks if a user or guild is banned from using the bot.

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

        if user_banned or guild_banned:
            await interaction.response.send_message("You or this server is banned from using the bot.", ephemeral=True)
            return False
        return True

    return application_checks.check(predicate)