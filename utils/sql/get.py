from utils.sql import get_db_connection
from typing import Any

def get(key: str, guild_id: int=0, user_id: int=0) -> Any:
    connection = get_db_connection()
    cursor = None
    try:
        cursor = connection.cursor()
        if user_id:
            cursor.execute(
                f"SELECT {key} FROM users WHERE id = %s",
                (user_id,)
            )
        else:
            cursor.execute(
                f"SELECT {key} FROM guilds WHERE id = %s",
                (guild_id,)
            )
        result = cursor.fetchone()
        if not result:
            return None
        if isinstance(result, dict):
            return result.get(key)
        return result[0]
    
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()
