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

import time


async def ping(message: nextcord.Message):
    test_message: nextcord.Message = await message.channel.send("...")
    start_time = time.time()
    await test_message.edit("....")
    elapsed_time = time.time() - start_time
    await test_message.edit(f"Pong!\n{elapsed_time * 1000}ms")


info = {
    "ping": {
        "category": "utilities",
        "aliases": ["latency"],
        "hidden_aliases": ["ms"],
        "available": ["text_command"],
        "visibility": "everyone",
        "user_permissions": [],
        "name": "ping_name",
        "desc": "ping_desc",
        "args": []
    }
}

cmd = CmdLocale(list(info.keys())[0], get_commands_locales(info))

class PingCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot


def setup(bot: commands.Bot):
    bot.add_cog(PingCog(bot))

# Text command handler wrapper that adapts to message handler signature
async def _message_handler(bot, message: nextcord.Message, lang: str, guild_prefix: str):
    await ping(message)
