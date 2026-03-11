from utils.sql import get_db_connection

def get(key: str, guild_id: int=0, user_id: int=0):
    connection = get_db_connection()
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
        return cursor.fetchone()[0]
    
    finally:
        cursor.close()
        connection.close()
