from utils.sql import get_db_connection

def get(key: str, guild_id: int):
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            f"SELECT {key} FROM guilds WHERE id = %s",
            (guild_id,)
        )
        return cursor.fetchone()[0]
    
    finally:
        cursor.close()
        connection.close()
