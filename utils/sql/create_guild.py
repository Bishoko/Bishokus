import nextcord
from functools import wraps
from utils.sql import get_db_connection, execute_sql_file

import json

with open('config/config.json') as config_file:
    config = json.load(config_file)
    default_prefix = config['default-prefix']
    default_language = config['default-language']
    default_confess_cooldown = config['default-confess-cooldown']
    

def ensure_guild_exists(guild_id):
    connection = get_db_connection()
    cursor = connection.cursor()

    # Check if the guild already exists
    cursor.execute("SELECT id FROM guilds WHERE id = %s", (guild_id,))
    result = cursor.fetchone()

    if result is None:
        # Guild doesn't exist, so we add it
        execute_sql_file(cursor, 'utils/sql/init_guild.sql', (guild_id, default_prefix, default_language, default_confess_cooldown,))

        connection.commit()

    cursor.close()
    connection.close()


def guild_db(func):
    """
    A decorator that ensures the guild exists in the database before executing the wrapped function.

    This decorator checks if the guild with the given ID exists in the database.
    If it doesn't exist, it creates the guild using the `ensure_guild_exists` function.

    Args:
        func (callable): The function to be wrapped.

    Returns:
        callable: The wrapped function.

    Usage:
        @guild_db
        def some_function(guild_id):
            # Function implementation
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        guild_id = args[0] if args else kwargs.get('guild_id')
        if not guild_id or isinstance(guild_id, nextcord.Message):
            message = args[0] if args else kwargs.get('message')
            if message and hasattr(message, 'guild'):
                guild_id = message.guild.id
        if guild_id:
            ensure_guild_exists(guild_id)
        return func(*args, **kwargs)
    return wrapper
