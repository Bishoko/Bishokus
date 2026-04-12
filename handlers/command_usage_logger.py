import json

import utils.sql as db
from utils.logger import log


def _increment_usage_counter(cursor, command_name: str, slash_command: bool):
    if slash_command:
        cursor.execute(
            "INSERT INTO command_usage_counters (command_name, usage_count, usage_count_slash, last_used) "
            "VALUES (%s, 1, 1, NOW()) ON DUPLICATE KEY UPDATE "
            "usage_count = COALESCE(usage_count, 0) + 1, "
            "usage_count_slash = COALESCE(usage_count_slash, 0) + 1, "
            "last_used = NOW()",
            (command_name,)
        )
        return

    cursor.execute(
        "INSERT INTO command_usage_counters (command_name, usage_count, usage_count_text, last_used) "
        "VALUES (%s, 1, 1, NOW()) ON DUPLICATE KEY UPDATE "
        "usage_count = COALESCE(usage_count, 0) + 1, "
        "usage_count_text = COALESCE(usage_count_text, 0) + 1, "
        "last_used = NOW()",
        (command_name,)
    )


def log_command_usage(
    command_name: str,
    user_id: int,
    guild_id: int | None,
    slash_command: bool,
    command_args: dict | list | None = None,
    command_args_str: str | None = None,
    text_command_alias: str | None = None,
):
    connection = None
    cursor = None

    try:
        connection = db.get_db_connection()
        cursor = connection.cursor()

        _increment_usage_counter(cursor, command_name, slash_command)

        cursor.execute(
            "INSERT INTO command_usage_logs ("
            "command_name, command_args, command_args_str, user_id, guild_id, slash_command, text_command_alias, timestamp"
            ") VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())",
            (
                command_name,
                json.dumps(command_args) if command_args is not None else None,
                command_args_str,
                user_id,
                guild_id,
                slash_command,
                text_command_alias,
            ),
        )

        connection.commit()
    except Exception as error:
        log.exception(error)
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()


async def handle_application_command_completion(interaction):
    """Persist slash command usage statistics in the database."""
    data = interaction.data or {}
    command_name = data.get("name", "unknown")

    log_command_usage(
        command_name=command_name,
        command_args=data.get("options", {}),
        user_id=interaction.user.id,
        guild_id=interaction.guild.id if interaction.guild else None,
        slash_command=True,
    )
