import nextcord
import re
import mysql.connector
from utils.sql import get_db_connection
from utils.sql.create_guild import guild_db
from utils.is_emoji import is_emoji

import json

with open('config/config.json', encoding='utf-8') as config_file:
    config = json.load(config_file)
    default_ratio_emoji_up = config.get('default-ratio-emoji-up', '👍')
    default_ratio_emoji_down = config.get('default-ratio-emoji-down', '👎')


@guild_db
def set(guild_id: int, client: nextcord.Client, up_emoji: str = None, down_emoji: str = None):
    """
    Sets new ratio emojis for a given guild ID in the database.

    Args:
        guild_id (int): The ID of the guild.
        client: The Discord client object.
        up_emoji (str, optional): The new up emoji to be set for the guild. Can be an emoji ID or a unicode emoji. Defaults to None.
        down_emoji (str, optional): The new down emoji to be set for the guild. Can be an emoji ID or a unicode emoji. Defaults to None.

    Raises:
        mysql.connector.Error: If there's an error while updating the database.
    """
    
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        def get_emoji(emoji):
            if emoji is None:
                return None

            if is_emoji(emoji):
                return emoji.encode('unicode-escape')
            
            elif ("<:" in emoji or "<a:" in emoji) and ">" in emoji:
                match = re.match(r'<a?:\w+:(\d+)>', emoji)
                if match:
                    emoji_id = int(match.group(1))
                    if client.get_emoji(emoji_id):
                        return emoji_id
                    else:
                        raise ValueError(f"Unknown emoji: {emoji}")
            
            raise ValueError(f"Invalid emoji: {emoji}")


        query = 'UPDATE guilds SET '
        params = []

        if up_emoji is not None:
            query += 'ratio_emoji_up = %s'
            params.append(get_emoji(up_emoji))

        if down_emoji is not None:
            if params:
                query += ', '
            query += 'ratio_emoji_down = %s'
            params.append(get_emoji(down_emoji))

        if params:
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
def get(guild_id: int, client: nextcord.Client, emoji_type: str = 'both') -> tuple:
    """
    Retrieves the ratio emojis for a given guild ID from the database.

    Args:
        guild_id (int): The ID of the guild.
        client: The Discord client object.
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

        def decode_if_needed(value):
            if isinstance(value, str):
                try:
                    return value.encode('latin-1').decode('unicode-escape')
                except:
                    return value
            return value

        def get_emoji(emoji):
            if emoji and not emoji.startswith('<'):
                try:
                    return client.get_emoji(int(emoji))
                except ValueError:
                    return emoji
            return emoji

        if emoji_type == 'up':
            up_emoji = get_emoji(decode_if_needed(result[0]) if result and result[0] is not None else decode_if_needed(default_ratio_emoji_up))
            return (up_emoji, None)
        elif emoji_type == 'down':
            down_emoji = get_emoji(decode_if_needed(result[0]) if result and result[0] is not None else decode_if_needed(default_ratio_emoji_down))
            return (None, down_emoji)
        else:  # 'both'
            if result and len(result) == 2:
                up_emoji = get_emoji(decode_if_needed(result[0]) if result[0] is not None else decode_if_needed(default_ratio_emoji_up))
                down_emoji = get_emoji(decode_if_needed(result[1]) if result[1] is not None else decode_if_needed(default_ratio_emoji_down))
                return (up_emoji, down_emoji)
            else:
                up_emoji = get_emoji(decode_if_needed(default_ratio_emoji_up))
                down_emoji = get_emoji(decode_if_needed(default_ratio_emoji_down))
                return (up_emoji, down_emoji)
    except mysql.connector.Error as err:
        print(f'Error: {err}')
        up_emoji = get_emoji(decode_if_needed(default_ratio_emoji_up))
        down_emoji = get_emoji(decode_if_needed(default_ratio_emoji_down))
        return (up_emoji, down_emoji)
    finally:
        cursor.close()
        conn.close()
