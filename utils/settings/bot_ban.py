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

