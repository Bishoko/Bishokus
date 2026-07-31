import nextcord
from nextcord.ext import commands, application_checks
from nextcord.application_command import slash_command, message_command
from utils.logger import log
from utils.get_commands_locales import get_commands_locales
from utils.locale_helpers import CmdLocale, get_slash_option
from utils import config, checks
from utils.settings.bot_ban import check_ban
from utils.languages import text
from utils.settings import prefix
from utils.settings.lang import get_lang
from utils.sql import get_db_connection

import subprocess  # nosec B404
import asyncio
import os


async def remote_text(message: nextcord.Message):
    command = message.content.strip()

    if not command:
        await message.channel.send("Please provide a command to execute.")
        return

    def run_command(cmd):
        try:
            result = subprocess.run(
                cmd,
                shell=True,  # nosec B602
                capture_output=True,
                text=True
            )
            return result.stdout, result.stderr, result.returncode
        except Exception as e:
            return "", str(e), -1

    # Doesn't block the event loop
    stdout, stderr, exit_code = await asyncio.to_thread(run_command, command)

    response = f"**Command:** `{command}`\n"
    response += f"**Exit Code:** {exit_code}\n"

    if stdout:
        response += f"**Output:**\n```\n{stdout}\n```\n"

    if stderr:
        response += f"**Error:**\n```\n{stderr}\n```\n"

    try:
        # If the response is too long, send it as a file
        if len(response) > 2000:
            os.remove(".logs/command_output.txt") if os.path.exists(".logs/command_output.txt") else None
            with open(".logs/command_output.txt", "w") as f:
                f.write(response)
            try:
                await message.reply(file=nextcord.File(".logs/command_output.txt"), mention_author=False)
            except Exception as e:
                log.debug(f"Failed to **reply** command output file: {e}")
                await message.channel.send(file=nextcord.File(".logs/command_output.txt"))
        else:
            await message.reply(response, mention_author=False)
    except Exception as e:
        await message.channel.send(f"An error occurred while sending the response: {e}")



info = {
    "remote": {
        "category": "bot_owner",
        "aliases": ["ssh"],
        "hidden_aliases": [],
        "available": ["text_command"],
        "visibility": "bot_owner",
        "user_permissions": ["bot_owner"],
        "name": "remote",
        "desc": "Sends commands to the server. yeah. (BOT OWNER ONLY)",
        "args": []
    }
}

cmd = CmdLocale(list(info.keys())[0], get_commands_locales(info))

class Remotecog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

def setup(bot: commands.Bot):
    bot.add_cog(Remotecog(bot))

# Text command handler wrapper that adapts to message handler signature
@checks.owner_only()
async def _message_handler(bot, message: nextcord.Message, lang: str, guild_prefix: str):
    await remote_text(message)
