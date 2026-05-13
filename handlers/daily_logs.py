import asyncio
import datetime
import nextcord
from nextcord.ext import tasks

from utils.logger import log
from utils.config import config
import utils.global_variables as gv


@tasks.loop(hours=24)
async def logs_loop():
    """Send bot logs in a channel every day at 23:59."""
    bot = gv.get('bot') or gv.get('client')
    if bot is None:
        log.warning("Bot instance not found in global variables, skipping logs loop.")
        return

    if bot.latency == 0:
        return
        
    # Get the channel to send logs to
    channel_id: int = config.get('logs-channel-id')

    if channel_id is None:
        log.warning("Logs channel ID not set in config, skipping logs loop.")
        return
        
    channel = bot.get_channel(channel_id)
    if channel is None:
        log.warning(f"Logs channel with ID {channel_id} not found, skipping logs loop.")
        return

    try:
        await channel.send(
            file=nextcord.File(log.log_file)
        )
    except Exception as e:
        log.exception(e, "Error sending logs file.")


@logs_loop.before_loop
async def before_logs_loop():
    # Ensure the bot instance is available
    bot = gv.get('bot') or gv.get('client')
    if bot is None:
        log.info("Waiting for bot instance to be available in global variables...")
        while bot is None:
            await asyncio.sleep(1)
            bot = gv.get('bot') or gv.get('client')

    # Wait until the bot is ready before calculating the first run time
    await bot.wait_until_ready()

    now = datetime.datetime.now()
    # Target today at 23:59:00
    target = now.replace(hour=23, minute=59, second=0, microsecond=0)
    if now >= target:
        target += datetime.timedelta(days=1)

    wait_seconds = (target - now).total_seconds()
    log.info(f"logs_loop scheduled to start at {target.isoformat()} (in {wait_seconds:.0f}s).")

    # Sleep until the target time
    await asyncio.sleep(wait_seconds)


def start_daily_logs_loop():
    """Starts the logs loop task."""
    logs_loop.start()
