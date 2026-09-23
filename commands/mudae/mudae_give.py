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

from utils.sql.mudae import normalize_search_text, find_owned_character, match_owned_character, get_character_owner, get_user_collection, transfer_character
from utils.mudae_views import TimedDisableView
from utils.get_user import get_user

GIVE_CONFIRM_WINDOW_SECONDS = 300  # 5 minutes to accept before the offer expires


class MudaeGiveConfirmView(TimedDisableView):
    def __init__(
        self, lang: str, giver_id: int, giver_name: str, receiver_id: int, receiver_name: str,
        character_uuid: str, character_name: str, guild_id: int
    ):
        super().__init__(timeout=GIVE_CONFIRM_WINDOW_SECONDS)
        self.lang = lang
        self.giver_id = giver_id
        self.giver_name = giver_name
        self.receiver_id = receiver_id
        self.receiver_name = receiver_name
        self.character_uuid = character_uuid
        self.character_name = character_name
        self.guild_id = guild_id
        self.accept_button.label = text('mudae_give_accept_button', lang)

    async def interaction_check(self, interaction: nextcord.Interaction) -> bool:
        if interaction.user.id != self.receiver_id:
            await interaction.response.send_message(
                text('mudae_give_not_for_you_error', self.lang), ephemeral=True
            )
            return False
        return True

    async def on_timeout(self):
        await super().on_timeout()
        if self._message is not None:
            try:
                await self._message.edit(content=text('mudae_give_expired', self.lang))
            except Exception as e:
                log.warning(f"Failed to mark expired mudae give offer: {e}")

    @nextcord.ui.button(label="Accept", style=nextcord.ButtonStyle.green)
    async def accept_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        # Re-verify in case the character was given away or re-rolled since the offer was made.
        current_owner = get_character_owner(self.character_uuid, self.guild_id)
        if current_owner != self.giver_id:
            button.disabled = True
            self.stop()
            await interaction.response.edit_message(
                content=text('mudae_give_no_longer_valid', self.lang), view=self
            )
            return

        transfer_character(self.character_uuid, self.receiver_id, self.guild_id)

        button.disabled = True
        self.stop()

        success_message = text('mudae_give_success', self.lang) \
            .replace('%giver%', self.giver_name) \
            .replace('%receiver%', self.receiver_name) \
            .replace('%character%', self.character_name)
        await interaction.response.edit_message(content=success_message, view=self)


async def _send_give_offer(
    lang: str, giver: nextcord.abc.User, receiver: nextcord.abc.User, character_query: str,
    guild_id: int, send
):
    if receiver.id == giver.id:
        await send(text('mudae_give_self_error', lang), ephemeral=True)
        return

    if receiver.bot:
        await send(text('mudae_give_bot_error', lang), ephemeral=True)
        return

    character = find_owned_character(giver.id, guild_id, character_query)
    if character is None:
        await send(
            text('mudae_give_not_owned_error', lang).replace('%query%', character_query),
            ephemeral=True
        )
        return

    view = MudaeGiveConfirmView(
        lang, giver.id, giver.display_name, receiver.id, receiver.display_name,
        character["uuid"], character["name"], guild_id
    )
    offer_message = text('mudae_give_offer', lang) \
        .replace('%giver%', giver.mention) \
        .replace('%receiver%', receiver.mention) \
        .replace('%character%', character["name"])

    sent = await send(offer_message, view=view)
    if sent is not None:
        view.bind_message(sent)
    return view


async def mudae_give_text(lang: str, message: nextcord.Message):
    original_content = message.content
    words = original_content.split()
    if not words:
        await message.reply(text('mudae_give_usage_error', lang), mention_author=False)
        return

    # The receiver can be a mention, an ID, a (possibly multi-word) name, or
    # implicit via reply - and the character name can also contain spaces - so
    # there's no fixed delimiter between the two parts of "!give <user> <character>".
    # Try every split point and keep the first one whose tail exactly matches
    # something the author actually owns; that's a strong, low-noise signal
    # for where the character name starts (find_owned_character requires a
    # near-exact name/alias match, not a loose substring one).
    collection = get_user_collection(message.author.id, message.guild.id)
    split_index = 1  # fallback: assume a single-word receiver, like the old mention-only behavior
    for candidate_index in range(len(words)):
        candidate_character_text = ' '.join(words[candidate_index:])
        if match_owned_character(collection, candidate_character_text):
            split_index = candidate_index
            break

    receiver_text = ' '.join(words[:split_index])
    character_query = ' '.join(words[split_index:])
    if not character_query:
        await message.reply(text('mudae_give_usage_error', lang), mention_author=False)
        return

    # get_user resolves off message.content (mention/ID/reply/fuzzy name match);
    # isolate the receiver portion so trailing character-name words don't throw it off.
    message.content = receiver_text
    receiver = await get_user(message)
    message.content = original_content

    async def send(content, **kwargs):
        kwargs.pop('ephemeral', None)
        return await message.reply(content, mention_author=False, **kwargs)

    await _send_give_offer(lang, message.author, receiver, character_query, message.guild.id, send)


async def mudae_give_slash(lang: str, interaction: nextcord.Interaction, member: nextcord.Member, character: str):
    async def send(content, **kwargs):
        await interaction.response.send_message(content, **kwargs)
        return None

    view = await _send_give_offer(lang, interaction.user, member, character, interaction.guild_id, send)
    if view is not None:
        view.bind_interaction(interaction)


info = {
    "give": {
        "category": "mudae",
        "aliases": [],
        "hidden_aliases": [],
        "available": ["slash_command", "text_command"],
        "dm_available": False,
        "visibility": "everyone",
        "user_permissions": [],
        "name": "give_name",
        "desc": "give_desc",
        "args": [
            {
                "name": "give_member_arg_name",
                "desc": "give_member_arg_desc",
                "required": True,
            },
            {
                "name": "give_character_arg_name",
                "desc": "give_character_arg_desc",
                "required": True,
                "autocomplete": True,
            },
        ]
    },
}

cmd = CmdLocale(list(info.keys())[0], get_commands_locales(info))


class MudaeGiveCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def character_autocomplete(self, interaction: nextcord.Interaction, current: str) -> dict:
        if not interaction.guild:
            return {}

        current = normalize_search_text(current)
        options = {}
        for character in get_user_collection(interaction.user.id, interaction.guild.id):
            if current and current not in normalize_search_text(character["name"]):
                continue
            label = character["name"]
            if character["series_name"]:
                label = f"{label} ({character['series_name']})"
            options[label[:100]] = character["uuid"]
            if len(options) >= 25:
                break
        return options

    @check_ban()
    @checks.guild_only()
    @slash_command(
        name=cmd.name,
        description=cmd.description,
        name_localizations=cmd.name_localizations,
        description_localizations=cmd.description_localizations,
    )
    async def give_command(
        self, interaction: nextcord.Interaction,
        member: nextcord.Member = get_slash_option(cmd.arg(0)),
        character: str = get_slash_option(cmd.arg(1)),
    ):
        await mudae_give_slash(get_lang(interaction), interaction, member, character)

    @give_command.on_autocomplete("character")
    async def on_character_autocomplete(self, interaction: nextcord.Interaction, character: str):
        await interaction.response.send_autocomplete(await self.character_autocomplete(interaction, character))


def setup(bot: commands.Bot):
    bot.add_cog(MudaeGiveCog(bot))


@checks.guild_only()
async def _message_handler(bot, message: nextcord.Message, lang: str, prefix_str: str):
    await mudae_give_text(lang, message)
