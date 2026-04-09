"""
Terrible code that converts the old bot data (before rewrite) to the new bot data (SQL).
Only converts guild data, because there's not much user data + i'm too lazy to convert sniper messages.
Sniper messages were stored in a text file named with the channel id only, not guild id, so it would require
the script to fetch the guild id for each channel id (17k channels...), so yeah i'm not doing that.
"""

import mysql.connector
import json
import os
with open('config/config.json', encoding='utf-8') as f:
    config = json.load(f)
    db_config = config['mysql']

def get_db_connection():
    """
    Establishes and returns a connection to the MySQL database.

    This function attempts to connect to the database using the configuration
    specified in the 'db_config' dictionary. If the initial connection fails
    due to a ProgrammingError (which might occur if the database doesn't exist),
    it will create the database and then attempt to connect again.

    Returns:
        mysql.connector.connection.MySQLConnection: A connection object to the MySQL database.

    Raises:
        mysql.connector.Error: If there's an error connecting to the database
        that isn't resolved by creating the database.

    Note:
        This function relies on the 'db_config' dictionary being properly
        populated with the necessary connection parameters.
    """
    try:
        return mysql.connector.connect(**db_config)
    except mysql.connector.errors.ProgrammingError:
        
        database = db_config['database']
        del db_config['database']
        
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        create_database(cursor, database)
        
        db_config['database'] = database
        return mysql.connector.connect(**db_config)
def create_database(cursor, db_name):
    """
    Creates a database if it does not exist.

    :param cursor: MySQL cursor object
    :param db_name: Name of the database to create
    """
    try:
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name} DEFAULT CHARACTER SET 'utf8'")
        print(f"Database {db_name} created or already exists.")
    except mysql.connector.Error as err:
        print(f"Failed to create database {db_name}: {err}")
        exit(1)

def get_guild_json(guild_id):
    path = old_db_dir + f'data/.GUILDS/{guild_id}.json'
    if os.path.exists(path):
        try:
            return json.load(open(path, encoding='utf-8')) or {}
        except json.JSONDecodeError:
            print(f"Error decoding JSON for guild {guild_id}. Returning empty dict.")
            return {}
    return {}

def get_user_json(user_id):
    path = old_db_dir + f'data/.USERS/{user_id}.json'
    if os.path.exists(path):
        try:
            return json.load(open(path, encoding='utf-8')) or {}
        except json.JSONDecodeError:
            print(f"Error decoding JSON for user {user_id}. Returning empty dict.")
            return {}
    return {}


def get_oomf_servers_ids(old_db_dir):
    with open(old_db_dir + "config/jaajservers.txt", "r", encoding='utf-8') as f:
        return [line.strip().split(" ")[0].strip() for line in f if line.strip()]
    
def get_oomf_ids(old_db_dir):
    with open(old_db_dir + "config/jaajeurs++.txt", "r", encoding='utf-8') as f:
        return [line.strip().split(" ")[0].strip() for line in f if line.strip()]


def get_guild_prefix(guild_id):
    data = json.load(open(old_db_dir + '2_musique/serversettings.json'))
    try:
        prefix = data[f"{guild_id}"]["prefix"]
        if prefix == '':
            prefix = '!'
    except:
        prefix = '!'
    return prefix.replace('"', '\\"')

def get_ratio_emoji(guild_id) -> str:
    guild_json = get_guild_json(guild_id)
    if not guild_json:
        return "NULL"
    ratio_emoji = guild_json.get("ratio_emoji", None)
    if not ratio_emoji or ratio_emoji in ["988926815101943868", "863206240497827850"]:
        return "NULL"
    return f'"{ratio_emoji}"'

def get_confess_channels(guild_id):
    guild_json = get_guild_json(guild_id)
    if not guild_json:
        return "[]"
    confess_settings = guild_json.get("confess", {})
    if not confess_settings:
        return "[]"
    
    confess_channels = [
        confess_settings.get("1"),
        confess_settings.get("2"),
        confess_settings.get("3"),
        confess_settings.get("4"),
        confess_settings.get("5"),
    ]
    confess_channels = [channel for channel in confess_channels if channel != "None"]
    
    return json.dumps(confess_channels)

def _get_all_guild_ids(old_db_dir):
    guild_ids = set()
    guilds_path = old_db_dir + 'data/.GUILDS/'
    if os.path.exists(guilds_path):
        for filename in os.listdir(guilds_path):
            if filename.endswith('.json') and filename[:-5].isdigit():
                guild_id = filename[:-5]  # Remove the .json extension
                guild_ids.add(guild_id)
    return guild_ids

def create_guild(guild_id):
    """
    This function is used to create the guilds table in the database.
    """
    connection = get_db_connection()
    cursor = connection.cursor()

    # Check if the guild already exists
    cursor.execute("SELECT id FROM guilds WHERE id = %s", (guild_id,))
    result = cursor.fetchone()

    if result is None:
        # Guild doesn't exist, so we add it
        command = f"""
INSERT INTO guilds (
    id,
    is_oomf,
    prefix,
    bot_language,
    ratio_emoji_up,
    ratio_emoji_down,
    wordplay_enabled,
    sniper_enabled,
    sniper,
    antisniper_backup,
    command_settings,
    confess_cooldown,
    confess_channels,
    confess_banned,
    bot_logs_enabled,
    bot_banned,
    bot_banned_type,
    bot_banned_reason,
    bot_banned_history
) VALUES (
    {guild_id},    -- id
    {str(True if str(guild_id) in oomf_ids else False).upper()}, -- is_oomf
    "{get_guild_prefix(guild_id)}",    -- prefix
    "fr",    -- bot_language
    {get_ratio_emoji(guild_id)},  -- ratio_emoji_up
    NULL,  -- ratio_emoji_down
    {str(get_guild_json(guild_id).get("jdm_switch", False)).upper()}, -- wordplay_enabled
    {str(get_guild_json(guild_id).get("snipe_switch", True)).upper()},  -- sniper_enabled
    '{empty_dict}',  -- sniper
    '{empty_dict}',  -- antisniper_backup
    '{empty_dict}',  -- command_settings
    {int(get_guild_json(guild_id).get("confess", {}).get("cooldown", 3))},    -- confess_cooldown
    '{str(get_confess_channels(guild_id))}',  -- confess_channels
    '{empty_dict}',  -- confess_banned
    FALSE, -- bot_logs_enabled
    FALSE, -- bot_banned
    NULL,  -- bot_banned_type
    NULL,  -- bot_banned_reason
    '[]'   -- bot_banned_history
)
        """
        try:
            cursor.execute(command,)
            

            connection.commit()

            cursor.close()
            connection.close()
        except Exception as e:
            print(f"Error creating guild {guild_id}: {e}")
            print(command)
            cursor.close()
            connection.close()
            raise e
    
def convert_guild_count_data():
    connection = get_db_connection()
    cursor = connection.cursor()
    
    with open(old_db_dir + "data/servers.txt", "r", encoding='utf-8') as f:
        lines = f.read().split("\n")
    for line in lines:
        if line.replace('\n', '').strip() == "":
            continue
        
        print(f"Converting guild count data line: {line}")
        
        time, _, count = line.partition(' | ')
        date, _, hour = time.partition(' ')
        
        count = count.strip()
        
        day, month, year = date.strip().split('/')
        hour, minutes, seconds = hour.strip().split(':')

        command = f"INSERT INTO guild_count (time, count) VALUES (TIMESTAMP('{year}-{month}-{day}', '{hour}:{minutes}:{seconds}'), {count})"
        cursor.execute(command)
        connection.commit()
    
    cursor.close()
    connection.close()

old_db_dir = ""
empty_dict = {}
oomf_servers_ids = []
oomf_ids = []
guild_ids = []

def convert_data():
    """
    This function is used to convert the previous bot version data (before rewrite) to the rewrite version (SQL).
    """
    global old_db_dir, empty_dict, oomf_servers_ids, oomf_ids, guild_ids
    
    old_db_dir = input("Enter the path to the old database directory: ")
    if old_db_dir.strip() == "":
        print("No path provided. Exiting.")
        return
    
    if old_db_dir[-1] != "/":
        old_db_dir += "/"
    
    
    oomf_servers_ids = get_oomf_servers_ids(old_db_dir)
    oomf_ids = get_oomf_ids(old_db_dir)
    
    guild_ids = _get_all_guild_ids(old_db_dir)
    print(f"Found {len(guild_ids)} guilds in the old database.")
    
    for guild_id in guild_ids:
        print(f"Converting guild {guild_id}...")
        create_guild(guild_id)
        
    convert_guild_count_data()
    

if __name__ == "__main__":
    convert_data()
