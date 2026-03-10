import nextcord
from nextcord.ext import commands, application_checks
from nextcord.application_command import slash_command, message_command
from utils.get_commands_locales import get_commands_locales
from utils.locale_helpers import CmdLocale, get_slash_option
from utils import config
from utils.settings.bot_ban import check_ban
from utils.languages import text
from utils.settings import prefix
from utils.settings.lang import get_lang

from utils.settings import bot_ban

info = {
    "ban_user": {
        "category": "bot_owner",
        "aliases": ["banuser", "user_ban"],
        "hidden_aliases": ["ban_u", "uban"],
        "available": ["slash_command"],
        "visibility": "bot_owner",
        "user_permissions": ["bot_owner"],
        "name": "ban_user",
        "desc": "Ban a user from using the bot (BOT OWNER ONLY)",
        "args": [
            {
                "name": "user_id",
                "desc": "The ID of the user to ban."
            },
            {
                "name": "ban_type",
                "desc": "The type of ban to apply.",
                "choices": {
                    "Default - default option in config": "default",
                    "Banned Message - inform users that the user is banned": "banned_message",
                    "Sulks - don't respond to the user anymore": "sulks"
                }
            },
            {
                "name": "reason",
                "desc": "The reason for the ban",
                "required": False
            }
        ]
    },
    "unban_user": {
        "category": "bot_owner",
        "aliases": ["unbanuser", "user_unban"],
        "hidden_aliases": ["unban_u"],
        "available": ["slash_command"],
        "visibility": "bot_owner",
        "user_permissions": ["bot_owner"],
        "name": "unban_user",
        "desc": "Unban a user from using the bot (BOT OWNER ONLY)",
        "args": [
            {
                "name": "user_id",
                "desc": "The ID of the user to unban."
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

class BanUserCog(commands.Cog):
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
    async def ban_user(self, interaction: nextcord.Interaction,
        user: nextcord.User = get_slash_option(cmd_ban.arg(0)),
        ban_type: str = get_slash_option(cmd_ban.arg(1)),
        reason: str = get_slash_option(cmd_ban.arg(2))
    ):
        bot_ban.ban_user(user.id, ban_type, reason)
        await interaction.response.send_message(
            f"User `{user.name} ({user.id})` has been banned successfully.\n\n"
            f"Reason: `{reason}`"
        )

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
    async def unban_user(self, interaction: nextcord.Interaction,
        user: nextcord.User = get_slash_option(cmd_unban.arg(0)),
        confirmation: str = get_slash_option(cmd_unban.arg(1))
    ):
        if confirmation.lower() != 'yes':
            await interaction.response.send_message(f"Unban operation for `{user.name} ({user.id})` cancelled.")
            return

        if not bot_ban.is_banned(user.id):
            await interaction.response.send_message(f"User `{user.name} ({user.id})` is not banned.")
            return

        bot_ban.unban_user(user.id)

        if bot_ban.is_banned(user.id):
            await interaction.response.send_message(
                f"Looks like there's an SQL error or something, but `{user.name} ({user.id})` isn't banned."
            )
        else:
            await interaction.response.send_message(
                f"User `{user.name} ({user.id})` has been unbanned successfully."
            )


def setup(bot: commands.Bot):
    bot.add_cog(BanUserCog(bot))
