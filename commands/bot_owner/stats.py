import nextcord
from nextcord.ext import commands, application_checks
from nextcord.application_command import slash_command, message_command
from utils.logger import log
from utils.get_commands_locales import get_commands_locales
from utils.locale_helpers import CmdLocale, get_slash_option
from utils import config
from utils.settings.bot_ban import check_ban
from utils.languages import text
from utils.settings import prefix
from utils.settings.lang import get_lang
from utils.sql import get_db_connection

from io import BytesIO


def _row_values(row, keys: tuple[str, ...]):
    if row is None:
        return tuple(0 for _ in keys)
    if isinstance(row, dict):
        return tuple(row.get(key, 0) for key in keys)
    return row


def _format_timestamp(value):
    if value is None:
        return "Never"
    try:
        return f"<t:{int(value.timestamp())}:R>"
    except Exception:
        return str(value)


def _safe_int(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _build_ascii_graph(top_commands: list[tuple[str, int]], max_bar_size: int = 20) -> str:
    if not top_commands:
        return "No command usage data yet."

    max_usage = max(usage for _, usage in top_commands) or 1
    lines = []
    for command_name, usage in top_commands:
        label = (command_name or "unknown")[:14]
        bar_length = int((usage / max_usage) * max_bar_size) if usage > 0 else 0
        if usage > 0 and bar_length == 0:
            bar_length = 1
        bar = "#" * bar_length
        lines.append(f"{label:<14} | {bar:<{max_bar_size}} {usage}")

    return "```text\n" + "\n".join(lines) + "\n```"

async def stats_commands_usage(interaction: nextcord.Interaction):
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            "SELECT COUNT(*) AS commands_count, "
            "COALESCE(SUM(usage_count), 0) AS total_usage, "
            "COALESCE(SUM(usage_count_slash), 0) AS slash_usage, "
            "COALESCE(SUM(usage_count_text), 0) AS text_usage, "
            "MAX(last_used) AS last_used "
            "FROM command_usage_counters"
        )
        counters_row = _row_values(
            cursor.fetchone(),
            ("commands_count", "total_usage", "slash_usage", "text_usage", "last_used"),
        )
        commands_count, total_usage, slash_usage, text_usage, last_used = counters_row

        cursor.execute(
            "SELECT COUNT(*) AS logs_count, "
            "COUNT(DISTINCT user_id) AS unique_users, "
            "COUNT(DISTINCT guild_id) AS unique_guilds, "
            "COALESCE(SUM(CASE WHEN slash_command = 1 THEN 1 ELSE 0 END), 0) AS slash_logs, "
            "COALESCE(SUM(CASE WHEN slash_command = 0 THEN 1 ELSE 0 END), 0) AS text_logs, "
            "MIN(timestamp) AS first_log, "
            "MAX(timestamp) AS last_log "
            "FROM command_usage_logs"
        )
        logs_row = _row_values(
            cursor.fetchone(),
            ("logs_count", "unique_users", "unique_guilds", "slash_logs", "text_logs", "first_log", "last_log"),
        )
        logs_count, unique_users, unique_guilds, slash_logs, text_logs, first_log, last_log = logs_row

        cursor.execute(
            "SELECT COUNT(*) AS logs_24h "
            "FROM command_usage_logs "
            "WHERE timestamp >= DATE_SUB(NOW(), INTERVAL 24 HOUR)"
        )
        logs_24h = _row_values(cursor.fetchone(), ("logs_24h",))[0]

        cursor.execute(
            "SELECT command_name, COALESCE(usage_count, 0) AS total_usage "
            "FROM command_usage_counters "
            "ORDER BY total_usage DESC "
            "LIMIT 8"
        )
        top_rows = cursor.fetchall() or []
        top_commands = []
        for row in top_rows:
            if isinstance(row, dict):
                top_commands.append((str(row.get("command_name", "unknown")), _safe_int(row.get("total_usage", 0))))
                continue
            top_commands.append((str(row[0]), _safe_int(row[1])))

        embed = nextcord.Embed(
            title="Command Usage Statistics",
            description="Live statistics from command usage counters and logs.",
            color=config.get("embed-color")
        )

        embed.add_field(
            name="Counters",
            value=(
                f"Tracked commands: **{commands_count}**\n"
                f"Total uses: **{total_usage}**\n"
                f"Slash uses: **{slash_usage}**\n"
                f"Text uses: **{text_usage}**\n"
                f"Last used: **{_format_timestamp(last_used)}**"
            ),
            inline=False,
        )

        embed.add_field(
            name="Logs",
            value=(
                f"Total log entries: **{logs_count}**\n"
                f"Last 24h: **{logs_24h}**\n"
                f"Unique users: **{unique_users}**\n"
                f"Unique guilds: **{unique_guilds}**\n"
                f"Slash/Text log ratio: **{slash_logs}/{text_logs}**\n"
                f"First log: **{_format_timestamp(first_log)}**\n"
                f"Latest log: **{_format_timestamp(last_log)}**"
            ),
            inline=False,
        )

        embed.add_field(
            name="Top Commands Graph",
            value=_build_ascii_graph(top_commands),
            inline=False,
        )

        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception as error:
        log.exception(error, "Error while building command usage statistics")
        if interaction.response.is_done():
            await interaction.followup.send(
                "Failed to load command usage statistics.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "Failed to load command usage statistics.",
                ephemeral=True
            )
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()

async def stats_servers(interaction: nextcord.Interaction):
    connection = None
    cursor = None

    try:
        import pandas as pd
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        from matplotlib.ticker import MaxNLocator

        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            "SELECT `time`, `count` FROM guild_count ORDER BY `time` DESC LIMIT 50"
        )
        rows = list(reversed(cursor.fetchall() or []))

        raw_points = []
        for row in rows:
            if isinstance(row, dict):
                ts = row.get("time")
                count = _safe_int(row.get("count", 0))
            else:
                ts, count = row[0], _safe_int(row[1])

            if ts is None:
                continue

            raw_points.append((ts, count))

        if not raw_points:
            if interaction.response.is_done():
                await interaction.followup.send("No server count data yet.", ephemeral=True)
            else:
                await interaction.response.send_message("No server count data yet.", ephemeral=True)
            return

        df = pd.DataFrame(raw_points, columns=["time", "count"])
        df["time"] = pd.to_datetime(df["time"], errors="coerce")
        df = df.dropna(subset=["time"]).sort_values("time")

        if df.empty:
            if interaction.response.is_done():
                await interaction.followup.send("No server count data yet.", ephemeral=True)
            else:
                await interaction.response.send_message("No server count data yet.", ephemeral=True)
            return

        latest_count = _safe_int(df["count"].iloc[-1])

        fig, ax = plt.subplots(figsize=(10, 7.2), dpi=120)
        ax.plot(df["time"], df["count"], marker="o", linewidth=2)
        ax.set_title("Server Count Over Time")
        ax.set_xlabel("Datetime (last 50 entries)")
        ax.set_ylabel("Server Count")
        ax.yaxis.set_major_locator(MaxNLocator(integer=True, nbins=20))

        date_locator = mdates.AutoDateLocator(minticks=6, maxticks=10)
        date_formatter = mdates.ConciseDateFormatter(date_locator)
        ax.xaxis.set_major_locator(date_locator)
        ax.xaxis.set_major_formatter(date_formatter)

        ax.grid(True, alpha=0.3)
        plt.xticks(rotation=45, ha="right")
        fig.tight_layout()

        image_buffer = BytesIO()
        fig.savefig(image_buffer, format="png")
        plt.close(fig)
        image_buffer.seek(0)

        chart_file = nextcord.File(fp=image_buffer, filename="server_count_graph.png")

        embed = nextcord.Embed(
            title="Server Count Statistics",
            description="Server count history from the database.",
            color=config.get("embed-color")
        )

        embed.add_field(
            name="Latest Count",
            value=f"**{latest_count}** servers - **{_format_timestamp(df['time'].iloc[-1])}**",
            inline=False,
        )
        embed.set_image(url="attachment://server_count_graph.png")

        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, file=chart_file, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, file=chart_file, ephemeral=True)
    except Exception as e:
        log.exception(e, "Error while building server statistics")
        if interaction.response.is_done():
            await interaction.followup.send(
                "Failed to load server statistics.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "Failed to load server statistics.",
                ephemeral=True
            )
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()


async def stats_slash(lang: str, interaction: nextcord.Interaction, category: str):
    if category == "commands_usage":
        await stats_commands_usage(interaction)
    elif category == "servers":
        await stats_servers(interaction)

    return


info = {
    "stats": {
        "category": "bot_owner",
        "aliases": [],
        "hidden_aliases": ["statistics"],
        "available": ["slash_command"],
        "visibility": "bot_owner",
        "user_permissions": ["bot_owner"],
        "name": "stats",
        "desc": "Show bot statistics (BOT OWNER ONLY)",
        "args": [
            {
                "name": "category",
                "desc": "The category of statistics to display.",
                "choices": {
                    "Commands usage statistics": "commands_usage",
                    "Server count graph": "servers",
                }
            },
        ]
    }
}

cmd = CmdLocale(list(info.keys())[0], get_commands_locales(info))

class StatsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @check_ban()
    @slash_command(
        guild_ids=[config.get('bot-guild'), config.get('testing-guild')],
        name=cmd.name,
        description=cmd.description,
        name_localizations=cmd.name_localizations,
        description_localizations=cmd.description_localizations,
        default_member_permissions=None,
    )
    async def stats_command(self, interaction: nextcord.Interaction,
        category: str = get_slash_option(cmd.arg(0))
    ):
        await stats_slash(get_lang(interaction), interaction, category)


def setup(bot: commands.Bot):
    bot.add_cog(StatsCog(bot))
