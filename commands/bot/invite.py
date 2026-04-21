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

import random

BOT_GUILD = config.get("bot-guild")
BOT_THUMBNAIL_URL = config.get("bot-avatar-url")
BOT_PAGE_URL = config.get("bot-page-url")
SUPPORT_SERVER_URL = config.get("support-server-url")
INVITE_URL = config.get("invite-url")
VOTE_URL = config.get("bot-vote-url")


class InviteView(nextcord.ui.View):
    def __init__(self, bot: commands.bot, lang: str):
        super().__init__()
        self.add_item(nextcord.ui.Button(
            label=text("invite_invite_link", lang),
            url=INVITE_URL,
            style=nextcord.ButtonStyle.link,
            emoji=bot.get_emoji(946583577372536864)
        ))
        self.add_item(nextcord.ui.Button(
            label=text("invite_support_server", lang),
            url=SUPPORT_SERVER_URL,
            style=nextcord.ButtonStyle.link
        ))
        self.add_item(nextcord.ui.Button(
            label=text("invite_bot_page", lang),
            url=BOT_PAGE_URL,
            style=nextcord.ButtonStyle.link
        ))

def _build_invite_embed(bot: commands.Bot, lang: str) -> nextcord.Embed:
    support_server_member_count = str(bot.get_guild(BOT_GUILD).member_count)
    
    bishokus_emoji = str(bot.get_emoji(946583577372536864))
    
    laugh_emoji = random.choice([
        "<a:yellowlaugh:1480581617960357908>",
        "<a:yellowlaugh:1480581617960357908>",
        "<a:yellowlaugh:1480581617960357908>",
        "<:superjoy:573231729800642570>",
        "<:shybimbo:1480581796109357199>",
        ":joy::rofl:",
    ])
    
    joy_emoji = random.choice([
        "<:kick_feet:1480581817395450008>",
        "<:kick_feet:1480581817395450008>",
        "<:kick_feet:1480581817395450008>",
        "<a:lebron:1480588484870672395>",
        "<:dab:1481067941972807864>",
        "<a:DuckShaker:1481068127046471773>",
        "<a:lettrej:1481068305048535040> ",
        "<a:monchienlol:1481068347880771787>",
        "<a:lezgongue:1481068519083737301>",
        "<a:skull:1481068570401046661>",
    ])

    embed = nextcord.Embed(
        title=text("invite_embed_title", lang),
        description=text("invite_embed_desc", lang).replace("%invite_url%", INVITE_URL),
        color=config.get("embed-color")
    )
    embed.set_thumbnail(url=BOT_THUMBNAIL_URL)

    embed.add_field(
        name=bishokus_emoji + " " + text("invite_field1_title", lang),
        value=text("invite_field1_desc", lang).replace("%laugh_emoji%", laugh_emoji)
        + "\n"
        + text("invite_field1_desc_l2", lang),
        inline=False,
    )
    
    # embed.add_field(
    #     name=text("invite_field2_title", lang),
    #     value=text("invite_field2_desc", lang).replace("%vote_url%", VOTE_URL) + "\n" +
    #           text("invite_field2_desc_l2", lang),
    #     inline=False
    # )
    
    embed.add_field(
        name=text("invite_field3_title", lang),
        value=text("invite_field3_desc", lang).replace(
            "%support_server_url%", SUPPORT_SERVER_URL
        )
        + "\n"
        + text("invite_field3_desc_l2", lang)
        .replace("%joy_emoji%", joy_emoji)
        .replace("%member_count%", support_server_member_count),
        inline=False,
    )

    return embed


async def invite_text(bot: commands.Bot, lang: str, message: nextcord.Message):
    await message.reply(
        embed=_build_invite_embed(bot, lang),
        view=InviteView(bot, lang),
        mention_author=False
    )

async def invite_slash(bot: commands.Bot, lang: str, interaction: nextcord.Interaction):
    await interaction.response.send_message(
        embed=_build_invite_embed(bot, lang),
        view=InviteView(bot, lang)
    )


info = {
    "invite": {
        "category": "bot",
        "aliases": [],
        "hidden_aliases": ["invit", "botinvite", "invitebot", "invitelink", "invite_link", "inv",
                           "add", "addme", "addbot", "botadd"],
        "available": ["slash_command", "text_command"],
        "visibility": "everyone",
        "user_permissions": [],
        "name": "invite_name",
        "desc": "invite_desc",
        "args": []
    }
}

cmd = CmdLocale(list(info.keys())[0], get_commands_locales(info))

class InviteCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @check_ban()
    @slash_command(
        name=cmd.name,
        description=cmd.description,
        name_localizations=cmd.name_localizations,
        description_localizations=cmd.description_localizations
    )
    async def invite_command(self, interaction: nextcord.Interaction):
        await invite_slash(self.bot, get_lang(interaction), interaction)


def setup(bot: commands.Bot):
    bot.add_cog(InviteCog(bot))

async def _message_handler(bot, message: nextcord.Message, lang: str, guild_prefix: str):
    await invite_text(bot, lang, message)
