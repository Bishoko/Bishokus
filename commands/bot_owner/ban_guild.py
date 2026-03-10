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

from utils.settings import bot_ban


async def bot_ban_guild(interaction: nextcord.Interaction, guild_id: int, ban_type: str, reason: str):
    guild = interaction.client.get_guild(int(guild_id))
    guild_name = guild.name if guild else "Unknown Guild"

    bot_ban.ban_guild(guild_id, ban_type, reason.lower())
    
    instantleave_success = ""
    if ban_type and ban_type.lower() == 'instant_leave':
        instantleave_success = "Instant leave success: False :/"
        guild = interaction.client.get_guild(int(guild_id))
        if guild:
            await guild.leave()
            instantleave_success = "Instant leave success: True :D"
            

    await interaction.response.send_message(
        f"Guild `{guild_name} ({guild_id})` has been banned successfully.\n" \
        f"Owner: `{guild.owner.name} ({guild.owner_id})`\n" \
        f"\n" \
        f"Reason: `{reason}`\n" \
        f"{instantleave_success}"
    )
    
    
async def bot_unban_guild(interaction: nextcord.Interaction, guild_id: int, confirmation: str):
    if confirmation.lower() != 'yes':
        await interaction.response.send_message("Unban operation cancelled.")
        return

    if not bot_ban.is_banned(guild_id, is_guild=True):
        await interaction.response.send_message("Guild is not banned.")
        return

    guild = interaction.client.get_guild(int(guild_id))
    guild_name = guild.name if guild else "Unknown Guild"

    bot_ban.unban_guild(guild_id)
    
    if bot_ban.is_banned(guild_id, is_guild=True):
        await interaction.response.send_message(f"Looks like there's an SQL error or something, but the guild `{guild_name} ({guild_id})` isn't banned.")
    else:
        await interaction.response.send_message(f"Guild `{guild_name} ({guild_id})` has been unbanned successfully.\nOwner: `{guild.owner.name} ({guild.owner_id})`")


info = {
    "ban_guild": {
        "category": "bot_owner",
        "aliases": ["banguild", "guild_ban", "server_ban", "ban_server"],
        "hidden_aliases": ["ban_g", "gban", "sban", "bans"],
        "available": ["slash_command"],
        "visibility": "bot_owner",
        "user_permissions": ["bot_owner"],
        "name": "ban_guild",
        "desc": "Ban a server from using the bot (BOT OWNER ONLY)",
        "args": [
            {
                "name": "guild_id",
                "desc": "The ID of the guild to ban."
            },
            {
                "name": "ban_type",
                "desc": "The type of ban to apply.",
                "choices": {
                    "Default - default option in config": "default",
                    "Banned Message - inform users that the server is banned": "banned_message",
                    "Sulks - don't even respond to the members anymore": "sulks",
                    "Instant Leave": "instant_leave"
                }
            },
            {
                "name": "reason",
                "desc": "The reason for the ban",
                "required": False
            }
        ]
    },
    "unban_guild": {
        "category": "bot_owner",
        "aliases": ["unbanguild", "guild_unban", "server_unban", "unban_server"],
        "hidden_aliases": ["unban_g"],
        "available": ["slash_command"],
        "visibility": "bot_owner",
        "user_permissions": ["bot_owner"],
        "name": "unban_guild",
        "desc": "Unban a server from using the bot (BOT OWNER ONLY)",
        "args": [
            {
                "name": "guild_id",
                "desc": "The ID of the guild to unban."
            },
            {
                "name": "confirmation",
                "desc": "type 'yes'"
            }
        ]
    },
}

locales = get_commands_locales(info)

cmd_ban = CmdLocale(list(info.keys())[0], locales)
cmd_unban = CmdLocale(list(info.keys())[1], locales)

class BanGuildCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @check_ban()
    @application_checks.is_owner()
    @slash_command(
        guild_ids=[config.get('bot-guild'), config.get('testing-guild')],
        name=cmd_ban.name,
        description=cmd_ban.description,
        name_localizations=cmd_ban.name_localizations,
        description_localizations=cmd_ban.description_localizations,
        default_member_permissions=None,
    )
    async def ban_guild(self, interaction: nextcord.Interaction,
        guild: str = get_slash_option(cmd_ban.arg(0)),
        type: str = get_slash_option(cmd_ban.arg(1)),
        reason: str = get_slash_option(cmd_ban.arg(2))
    ):
        await bot_ban_guild(interaction, guild, type, reason)

    @check_ban()
    @application_checks.is_owner()
    @slash_command(
        guild_ids=[config.get('bot-guild'), config.get('testing-guild')],
        name=cmd_unban.name,
        description=cmd_unban.description,
        name_localizations=cmd_unban.name_localizations,
        description_localizations=cmd_unban.description_localizations,
        default_member_permissions=None,
    )
    async def unban_guild(self, interaction: nextcord.Interaction,
        guild: str = get_slash_option(cmd_unban.arg(0)),
        confirmation: str = get_slash_option(cmd_unban.arg(1))
    ):
        await bot_unban_guild(interaction, guild, confirmation)


def setup(bot: commands.Bot):
    bot.add_cog(BanGuildCog(bot))
