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
import dateparser
import utils.vip as vip

info = {
    "vip_add": {
        "category": "bot_owner",
        "aliases": [],
        "hidden_aliases": ["addvip", "add_vip", "vip_add", "vipadd"],
        "available": ["slash_command"],
        "visibility": "bot_owner",
        "user_permissions": ["bot_owner"],
        "name": "vip_add",
        "desc": "Add a VIP user (BOT OWNER ONLY)",
        "args": [
            {
                "name": "user_id",
                "desc": "The ID of the user to add as VIP."
            },
            {
                "name": "vip_end",
                "desc": "The end date of the VIP status."
            }
        ]
    },
    "vip_remove": {
        "category": "bot_owner",
        "aliases": [],
        "hidden_aliases": ["removevip", "remove_vip", "vip_remove", "vipremove"],
        "available": ["slash_command"],
        "visibility": "bot_owner",
        "user_permissions": ["bot_owner"],
        "name": "vip_remove",
        "desc": "Remove a VIP user (BOT OWNER ONLY)",
        "args": [
            {
                "name": "user_id",
                "desc": "The ID of the user to remove from VIP."
            }
        ]
    },
}

locales = get_commands_locales(info)

cmd_add_vip = CmdLocale(list(info.keys())[0], locales)
cmd_remove_vip = CmdLocale(list(info.keys())[1], locales)

class ManageVipCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @check_ban()
    @application_checks.is_owner()
    @slash_command(
        guild_ids=[config.get('bot-guild'), config.get('testing-guild')],
        name=cmd_add_vip.name,
        description=cmd_add_vip.description,
        name_localizations=cmd_add_vip.name_localizations,
        description_localizations=cmd_add_vip.description_localizations,
        default_member_permissions=None,
    )
    async def add_vip(self, interaction: nextcord.Interaction,
        user: nextcord.User = get_slash_option(cmd_add_vip.arg(0)),
        vip_end: str = get_slash_option(cmd_add_vip.arg(1))
    ):
        vip_end_date = dateparser.parse(
            vip_end,
            languages=["fr", "en"],
            locales=["fr", "en"],
            region="fr"
        )
        if vip_end_date is None:
            await interaction.response.send_message(
                "Invalid date format",
                ephemeral=True
            )
            return
        
        timestamp = int(vip_end_date.timestamp())
        timestamp_now = int(time.time())
        if timestamp <= timestamp_now:
            await interaction.response.send_message(
                "The VIP end date must be in the future.",
                ephemeral=True
            )
            return
        
        vip.add(user.id, vip_end_date)
        await interaction.response.send_message(
            f"User `{user.name} ({user.id})` has been added as VIP successfully.\n\n"
            f"VIP End Date: <t:{timestamp}:R>\n<t:{timestamp}:F>"
        )

    @check_ban()
    @application_checks.is_owner()
    @slash_command(
        guild_ids=[config.get('bot-guild'), config.get('testing-guild')],
        name=cmd_remove_vip.name,
        description=cmd_remove_vip.description,
        name_localizations=cmd_remove_vip.name_localizations,
        description_localizations=cmd_remove_vip.description_localizations,
        default_member_permissions=None,
    )
    async def remove_vip(self, interaction: nextcord.Interaction,
        user: nextcord.User = get_slash_option(cmd_remove_vip.arg(0))
    ):
        vip.remove(user.id)
        await interaction.response.send_message(
            f"User `{user.name} ({user.id})` has been removed from VIP successfully."
        )


def setup(bot: commands.Bot):
    bot.add_cog(ManageVipCog(bot))
