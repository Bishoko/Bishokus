import mysql.connector
from utils.sql import get_db_connection
from utils.sql.create_guild import guild_db

import json

with open('config/config.json', encoding='utf-8') as config_file:
    config = json.load(config_file)
    default_ratio_emoji_up = config.get('default-ratio-emoji-up', '👍')
    default_ratio_emoji_down = config.get('default-ratio-emoji-down', '👎')


@guild_db
def set(guild_id: int, up_emoji_id: int = None, down_emoji_id: int = None):
    """
    Sets new ratio emojis for a given guild ID in the database.

    Args:
        guild_id (int): The ID of the guild.
        up_emoji_id (int, optional): The new up emoji ID to be set for the guild. Defaults to None.
        down_emoji_id (int, optional): The new down emoji ID to be set for the guild. Defaults to None.

    Raises:
        mysql.connector.Error: If there's an error while updating the database.
    """
    
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        query = 'UPDATE guilds SET '
        params = []
        if up_emoji_id is not None:
            query += 'ratio_emoji_up = %s'
            params.append(up_emoji_id)
        if down_emoji_id is not None:
            if params:
                query += ', '
            query += 'ratio_emoji_down = %s'
            params.append(down_emoji_id)
        query += ' WHERE id = %s'
        params.append(guild_id)

        cursor.execute(query, tuple(params))
        conn.commit()
    except mysql.connector.Error as err:
        print(f'Error: {err}')
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

@guild_db
def get(guild_id: int, emoji_type: str = 'both') -> tuple:
    """
    Retrieves the ratio emojis for a given guild ID from the database.

    Args:
        guild_id (int): The ID of the guild.
        emoji_type (str, optional): The type of emoji to retrieve. Can be 'up', 'down', or 'both'. Defaults to 'both'.

    Returns:
        tuple: A tuple containing the ratio emoji IDs for the guild. 
               If emoji_type is 'up', returns (up_emoji_id, None).
               If emoji_type is 'down', returns (None, down_emoji_id).
               If emoji_type is 'both', returns (up_emoji_id, down_emoji_id).
               If no emoji is found, the corresponding value will be the default value.

    Raises:
        mysql.connector.Error: If there's an error while querying the database.
        ValueError: If an invalid emoji_type is provided.
    """
    
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        if emoji_type not in ['up', 'down', 'both']:
            raise ValueError("emoji_type must be 'up', 'down', or 'both'")

        query = 'SELECT '
        if emoji_type in ['up', 'both']:
            query += 'ratio_emoji_up'
        if emoji_type == 'both':
            query += ', '
        if emoji_type in ['down', 'both']:
            query += 'ratio_emoji_down'
        query += ' FROM guilds WHERE id = %s'

        cursor.execute(query, (guild_id,))
        result = cursor.fetchone()

        if emoji_type == 'up':
            return (result[0] if result and result[0] is not None else default_ratio_emoji_up, None)
        elif emoji_type == 'down':
            return (None, result[0] if result and result[0] is not None else default_ratio_emoji_down)
        else:  # 'both'
            if result and len(result) == 2:
                return (result[0] if result[0] is not None else default_ratio_emoji_up,
                        result[1] if result[1] is not None else default_ratio_emoji_down)
            else:
                return (default_ratio_emoji_up, default_ratio_emoji_down)
    except mysql.connector.Error as err:
        print(f'Error: {err}')
        return (default_ratio_emoji_up, default_ratio_emoji_down)
    finally:
        cursor.close()
        conn.close()
