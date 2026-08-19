import mysql.connector
from mysql.connector import errorcode
from utils.logger import log
from utils.sql import get_db_connection
import io


def backup_database(db_name: str) -> str:
    """
    Creates a SQL backup of the database and returns it as a string.
    Works in both Docker containers and standalone environments.

    :param db_name: Name of the database to backup
    :return: SQL dump as string
    :raises Exception: If backup fails
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        sql_dump = io.StringIO()

        sql_dump.write("SET FOREIGN_KEY_CHECKS=0;\n")
        sql_dump.write("SET SQL_MODE='NO_AUTO_VALUE_ON_ZERO';\n\n")

        cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = %s", (db_name,))
        tables = cursor.fetchall()

        for (table_name,) in tables:
            sql_dump.write(f"\n-- Table: {table_name}\n")
            sql_dump.write(f"DROP TABLE IF EXISTS `{table_name}`;\n")

            cursor.execute(f"SHOW CREATE TABLE `{table_name}`")
            create_table = cursor.fetchone()[1]
            sql_dump.write(create_table + ";\n\n")

            cursor.execute(f"SELECT * FROM `{table_name}`")  # nosec B608
            rows = cursor.fetchall()

            if rows:
                cursor.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s", (db_name, table_name))  # nosec B608
                columns = [col[0] for col in cursor.fetchall()]
                columns_str = ", ".join([f"`{col}`" for col in columns])

                for row in rows:
                    values = []
                    for val in row:
                        if val is None:
                            values.append("NULL")
                        elif isinstance(val, (int, float)):
                            values.append(str(val))
                        else:
                            escaped = str(val).replace("\\", "\\\\").replace("'", "\\'")
                            values.append(f"'{escaped}'")

                    sql_dump.write(f"INSERT INTO `{table_name}` ({columns_str}) VALUES ({', '.join(values)});\n")  # nosec B608
                sql_dump.write("\n")

        sql_dump.write("SET FOREIGN_KEY_CHECKS=1;\n")
        return sql_dump.getvalue()

    except mysql.connector.Error as err:
        log.exception(err, f"Error backing up database {db_name}")
        raise
    finally:
        cursor.close()
        conn.close()


def restore_database(db_name: str, sql_content: str):
    """
    Restores a database from SQL content.
    Works in both Docker containers and standalone environments.

    :param db_name: Name of the database to restore to
    :param sql_content: SQL dump as string
    :raises Exception: If restore fails
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        statements = parse_sql_statements(sql_content)

        for statement in statements:
            if statement.strip():
                try:
                    cursor.execute(statement)
                except mysql.connector.Error as err:
                    if err.errno == errorcode.ER_SYNTAX_ERROR:
                        log.debug(f"Skipping statement due to syntax error: {statement[:100]}")
                    else:
                        raise

        conn.commit()

    except mysql.connector.Error as err:
        conn.rollback()
        log.exception(err, f"Error restoring database {db_name}")
        raise
    finally:
        cursor.close()
        conn.close()


def parse_sql_statements(sql_content: str) -> list:
    """
    Parses SQL content into individual statements.
    Handles multi-line statements and comments.

    :param sql_content: SQL dump as string
    :return: List of SQL statements
    """
    statements = []
    current_statement = ""
    in_string = False
    string_char = None
    escape_next = False

    for char in sql_content:
        if escape_next:
            current_statement += char
            escape_next = False
            continue

        if char == "\\":
            current_statement += char
            escape_next = True
            continue

        if char in ("'", '"') and not in_string:
            in_string = True
            string_char = char
            current_statement += char
        elif char == string_char and in_string:
            in_string = False
            string_char = None
            current_statement += char
        elif char == ";" and not in_string:
            current_statement += char
            statements.append(current_statement)
            current_statement = ""
        else:
            current_statement += char

    if current_statement.strip():
        statements.append(current_statement)

    return statements
