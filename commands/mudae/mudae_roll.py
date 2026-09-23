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

from utils.sql.mudae import (
    add_kakera_reward,
    build_image_url,
    claim_character,
    compute_kakera_reaction_reward,
    consume_roll,
    get_claim_status,
    get_rollable_character,
)
from utils.mudae_media import format_rank, get_kakera_button_emoji, get_kakera_emoji, resolve_character_image
from utils.mudae_views import TimedDisableView

import utils.global_variables as gv
from datetime import datetime

GENDER_ANY = None
GENDER_MALE = 1
GENDER_FEMALE = 2
GENDER_OTHER = 3

CLAIM_WINDOW_SECONDS = 150  # 2m30s to claim before the button stops responding
STEAL_BUFFER_SECONDS = 10  # only the roller can claim during this window


def _channel_allows_nsfw(channel) -> bool:
    is_nsfw = getattr(channel, "is_nsfw", None)
    if callable(is_nsfw):
        return is_nsfw()
    return False


def _format_duration(delta) -> str:
    total_minutes = max(int(delta.total_seconds() // 60), 0)
    hours, minutes = divmod(total_minutes, 60)
    if hours:
        return f"{hours}h {minutes} min"
    return f"{minutes} min"


def _resolve_display_name(guild: nextcord.Guild, user_id: int, lang: str) -> str:
    member = guild.get_member(user_id)
    if member:
        return member.display_name

    bot = gv.get('bot') or gv.get('client')
    user = bot.get_user(user_id) if bot else None
    if user:
        return user.display_name

    return text('mudae_unknown_user', lang)


def _resolve_avatar(guild: nextcord.Guild, user_id: int) -> str | None:
    member = guild.get_member(user_id)
    if not member:
        return None
    
    return str(member.guild_avatar or member.avatar or member.default_avatar)


class MudaeClaimView(TimedDisableView):
    def __init__(
        self, lang: str, character_uuid: str, character_name: str, kakera_value: int,
        guild_id: int, roller_id: int, roller_name: str
    ):
        super().__init__(timeout=CLAIM_WINDOW_SECONDS)
        self.lang = lang
        self.character_uuid = character_uuid
        self.character_name = character_name
        self.kakera_value = kakera_value
        self.guild_id = guild_id
        self.roller_id = roller_id
        self.roller_name = roller_name
        self.rolled_at = datetime.now()
        self.claimed = False
        self.claim_button.label = text('mudae_claim_button_label', lang)

    @nextcord.ui.button(label="Claim", style=nextcord.ButtonStyle.blurple)
    async def claim_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        if self.claimed:
            await interaction.response.send_message(
                text('mudae_already_claimed_error', self.lang).replace('%character%', self.character_name),
                ephemeral=True
            )
            return

        is_roller = interaction.user.id == self.roller_id
        elapsed = (datetime.now() - self.rolled_at).total_seconds()
        if not is_roller and elapsed < STEAL_BUFFER_SECONDS:
            # The roller gets priority for the first few seconds. Not
            # ephemeral on purpose, so the roller sees the steal attempt.
            steal_message = text('mudae_claim_steal_buffer_error', self.lang) \
                .replace('%user%', interaction.user.display_name) \
                .replace('%character%', self.character_name) \
                .replace('%roller%', self.roller_name)
            await interaction.response.send_message(steal_message)
            return

        can_claim, remaining = get_claim_status(interaction.user.id, self.guild_id)
        if not can_claim:
            cooldown_message = text('mudae_claim_cooldown_error', self.lang) \
                .replace('%user%', interaction.user.display_name) \
                .replace('%remaining%', _format_duration(remaining))
            await interaction.response.send_message(cooldown_message, ephemeral=False)
            return

        self.claimed = True

        try:
            claim_character(self.character_uuid, interaction.user.id, self.guild_id, self.kakera_value)
        except Exception as e:
            self.claimed = False
            log.exception(e, "Error claiming mudae character")
            await interaction.response.send_message(
                text('mudae_claim_error', self.lang),
                ephemeral=True
            )
            return

        button.disabled = True
        button.label = text('mudae_claimed_label', self.lang).replace('%user%', interaction.user.display_name)
        button.style = nextcord.ButtonStyle.green
        self.stop()

        await interaction.response.edit_message(view=self)
        message = text('mudae_claim_success', self.lang) \
            .replace('%user%', interaction.user.display_name) \
            .replace('%character%', str(self.character_name))
        await interaction.followup.send(message)


class MudaeKakeraReactView(TimedDisableView):
    """Shown instead of MudaeClaimView when the roll landed on a character
    someone already owns in this guild: it can't be claimed, but anyone can
    steal a smaller kakera reward, same as real Mudae."""

    def __init__(self, lang: str, roller_id: int, guild_id: int, reward: int):
        super().__init__(timeout=CLAIM_WINDOW_SECONDS)
        self.lang = lang
        self.roller_id = roller_id
        self.guild_id = guild_id
        self.reward = reward
        self.claimed = False
        self.react_button.label = str(reward)
        self.react_button.emoji = get_kakera_button_emoji()

    @nextcord.ui.button(label="0", style=nextcord.ButtonStyle.grey)
    async def react_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        if self.claimed:
            await interaction.response.send_message(
                text('mudae_kakera_already_claimed_error', self.lang),
                ephemeral=True
            )
            return

        self.claimed = True
        add_kakera_reward(interaction.user.id, self.guild_id, self.reward)

        button.disabled = True
        button.style = nextcord.ButtonStyle.green
        self.stop()

        await interaction.response.edit_message(view=self)
        react_message = text('mudae_kakera_react_success', self.lang) \
            .replace('%kakera_emoji%', config.get('default-mudae-emoji')) \
            .replace('%user%', interaction.user.display_name) \
            .replace('%kakera%', str(self.reward))
        await interaction.followup.send(react_message)


def _build_roll_embed(
    lang: str, character: dict, kakera_value: int, image_url: str | None, owner_name: str | None, owner_avatar: str | None
) -> nextcord.Embed:
    description_lines = [
        character['series_name'] or text('mudae_unknown_series', lang),
        f"{text('mudae_claims_label', lang)}: {format_rank(character['rank'], lang)}",
        f"{text('mudae_likes_label', lang)}: {format_rank(character['like_rank'], lang)}",
        f"{kakera_value} {get_kakera_emoji()}",
    ]

    embed = nextcord.Embed(
        title=character['name'],
        description="\n".join(description_lines),
        color=config.get('embed-color'),
    )

    if owner_name:
        embed.set_footer(
            text=text('mudae_belongs_to', lang).replace('%user%', owner_name),
            icon_url=owner_avatar
        )

    if image_url:
        embed.set_image(url=image_url)

    return embed


async def _perform_roll(
    lang: str, user_id: int, user_display_name: str, guild: nextcord.Guild, allow_nsfw: bool, gender: int | None
):
    """Returns (embed, view, image_file, error_message)."""
    allowed, remaining = consume_roll(user_id, guild.id)
    if not allowed:
        error = text('mudae_roll_cooldown_error', lang).replace('%reset%', _format_duration(remaining))
        return None, None, None, error

    character = get_rollable_character(gender, guild.id, allow_nsfw)
    if character is None:
        return None, None, None, text('mudae_no_characters_error', lang)

    # kakera_value is a cached column, kept fresh by the periodic stats
    # recompute job rather than derived here on every roll.
    kakera_value = character['kakera_value']

    image_path = character['images'][0] if character['images'] else None
    image_url, image_file = await resolve_character_image(build_image_url(image_path))

    owner_id = character['owner_id']
    if owner_id is None:
        embed = _build_roll_embed(lang, character, kakera_value, image_url, None, None)
        view = MudaeClaimView(
            lang, character['uuid'], character['name'], kakera_value, guild.id, user_id, user_display_name
        )
    else:
        owner_name = _resolve_display_name(guild, owner_id, lang)
        owner_avatar = _resolve_avatar(guild, owner_id)
        embed = _build_roll_embed(lang, character, kakera_value, image_url, owner_name, owner_avatar)
        reward = compute_kakera_reaction_reward(kakera_value)
        view = MudaeKakeraReactView(lang, user_id, guild.id, reward)

    return embed, view, image_file, None


async def mudae_roll_text(lang: str, message: nextcord.Message, gender: int | None):
    allow_nsfw = _channel_allows_nsfw(message.channel)
    embed, view, image_file, error = await _perform_roll(
        lang, message.author.id, message.author.display_name, message.guild, allow_nsfw, gender
    )

    if error:
        await message.reply(error, mention_author=False)
        return

    kwargs = {"embed": embed, "view": view, "mention_author": False}
    if image_file:
        kwargs["file"] = image_file
    sent_message = await message.reply(**kwargs)
    view.bind_message(sent_message)


async def mudae_roll_slash(lang: str, interaction: nextcord.Interaction, gender: int | None):
    allow_nsfw = _channel_allows_nsfw(interaction.channel)
    embed, view, image_file, error = await _perform_roll(
        lang, interaction.user.id, interaction.user.display_name, interaction.guild, allow_nsfw, gender
    )

    if error:
        await interaction.response.send_message(error, ephemeral=True)
        return

    kwargs = {"embed": embed, "view": view}
    if image_file:
        kwargs["file"] = image_file
    await interaction.response.send_message(**kwargs)
    view.bind_interaction(interaction)


def _build_status_message(lang: str, display_name: str, user_id: int, guild_id: int) -> str:
    can_claim, remaining = get_claim_status(user_id, guild_id)
    if can_claim:
        return text('mudae_status_can_claim', lang) \
            .replace('%user%', display_name) \
            .replace('%reset%', _format_duration(remaining))
    return text('mudae_status_cant_claim', lang) \
        .replace('%user%', display_name) \
        .replace('%remaining%', _format_duration(remaining))


async def mudae_status_text(lang: str, message: nextcord.Message):
    await message.reply(
        _build_status_message(lang, message.author.display_name, message.author.id, message.guild.id),
        mention_author=False
    )


async def mudae_status_slash(lang: str, interaction: nextcord.Interaction):
    await interaction.response.send_message(
        _build_status_message(lang, interaction.user.display_name, interaction.user.id, interaction.guild_id)
    )


info = {
    "m": {
        "category": "mudae",
        "aliases": ["mudae"],
        "hidden_aliases": [],
        "available": ["slash_command", "text_command"],
        "dm_available": False,
        "visibility": "everyone",
        "user_permissions": [],
        "name": "m_name",
        "desc": "m_desc",
        "args": []
    },
    "w": {
        "category": "mudae",
        "aliases": ["waifu"],
        "hidden_aliases": [],
        "available": ["slash_command", "text_command"],
        "dm_available": False,
        "visibility": "everyone",
        "user_permissions": [],
        "name": "w_name",
        "desc": "w_desc",
        "args": []
    },
    "h": {
        "category": "mudae",
        "aliases": ["husbando"],
        "hidden_aliases": [],
        "available": ["slash_command", "text_command"],
        "dm_available": False,
        "visibility": "everyone",
        "user_permissions": [],
        "name": "h_name",
        "desc": "h_desc",
        "args": []
    },
    "nb": {
        "category": "mudae",
        "aliases": ["nonbinary"],
        "hidden_aliases": [],
        "available": ["slash_command", "text_command"],
        "dm_available": False,
        "visibility": "everyone",
        "user_permissions": [],
        "name": "nb_name",
        "desc": "nb_desc",
        "args": []
    },
    "mu": {
        "category": "mudae",
        "aliases": [],
        "hidden_aliases": [],
        "available": ["slash_command", "text_command"],
        "dm_available": False,
        "visibility": "everyone",
        "user_permissions": [],
        "name": "mu_name",
        "desc": "mu_desc",
        "args": []
    },
}

locales = get_commands_locales(info)
cmd_m = CmdLocale("m", locales)
cmd_w = CmdLocale("w", locales)
cmd_h = CmdLocale("h", locales)
cmd_nb = CmdLocale("nb", locales)
cmd_mu = CmdLocale("mu", locales)


class MudaeRollCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @check_ban()
    @checks.guild_only()
    @slash_command(
        name=cmd_m.name,
        description=cmd_m.description,
        name_localizations=cmd_m.name_localizations,
        description_localizations=cmd_m.description_localizations,
    )
    async def m_command(self, interaction: nextcord.Interaction):
        await mudae_roll_slash(get_lang(interaction), interaction, GENDER_ANY)

    @check_ban()
    @checks.guild_only()
    @slash_command(
        name=cmd_w.name,
        description=cmd_w.description,
        name_localizations=cmd_w.name_localizations,
        description_localizations=cmd_w.description_localizations,
    )
    async def w_command(self, interaction: nextcord.Interaction):
        await mudae_roll_slash(get_lang(interaction), interaction, GENDER_FEMALE)

    @check_ban()
    @checks.guild_only()
    @slash_command(
        name=cmd_h.name,
        description=cmd_h.description,
        name_localizations=cmd_h.name_localizations,
        description_localizations=cmd_h.description_localizations,
    )
    async def h_command(self, interaction: nextcord.Interaction):
        await mudae_roll_slash(get_lang(interaction), interaction, GENDER_MALE)

    @check_ban()
    @checks.guild_only()
    @slash_command(
        name=cmd_nb.name,
        description=cmd_nb.description,
        name_localizations=cmd_nb.name_localizations,
        description_localizations=cmd_nb.description_localizations,
    )
    async def nb_command(self, interaction: nextcord.Interaction):
        await mudae_roll_slash(get_lang(interaction), interaction, GENDER_OTHER)

    @check_ban()
    @checks.guild_only()
    @slash_command(
        name=cmd_mu.name,
        description=cmd_mu.description,
        name_localizations=cmd_mu.name_localizations,
        description_localizations=cmd_mu.description_localizations,
    )
    async def mu_command(self, interaction: nextcord.Interaction):
        await mudae_status_slash(get_lang(interaction), interaction)


def setup(bot: commands.Bot):
    bot.add_cog(MudaeRollCog(bot))


# Text command handler wrappers that adapt to message handler signature
@checks.guild_only()
async def _message_handler_m(bot, message: nextcord.Message, lang: str, prefix_str: str):
    await mudae_roll_text(lang, message, GENDER_ANY)


@checks.guild_only()
async def _message_handler_w(bot, message: nextcord.Message, lang: str, prefix_str: str):
    await mudae_roll_text(lang, message, GENDER_FEMALE)


@checks.guild_only()
async def _message_handler_h(bot, message: nextcord.Message, lang: str, prefix_str: str):
    await mudae_roll_text(lang, message, GENDER_MALE)


@checks.guild_only()
async def _message_handler_nb(bot, message: nextcord.Message, lang: str, prefix_str: str):
    await mudae_roll_text(lang, message, GENDER_OTHER)


@checks.guild_only()
async def _message_handler_mu(bot, message: nextcord.Message, lang: str, prefix_str: str):
    await mudae_status_text(lang, message)


_message_handlers = {
    "m": _message_handler_m,
    "w": _message_handler_w,
    "h": _message_handler_h,
    "nb": _message_handler_nb,
    "mu": _message_handler_mu,
}
