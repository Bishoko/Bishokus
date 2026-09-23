import nextcord
from nextcord.ext import commands
from nextcord.application_command import slash_command
from utils.get_commands_locales import get_commands_locales
from utils.locale_helpers import CmdLocale, get_slash_option
from utils import config, checks
from utils.settings.bot_ban import check_ban
from utils.languages import text
from utils.settings.lang import get_lang

from utils.sql.mudae import normalize_search_text, divorce_character, find_owned_character, get_character_owner, get_user_collection
from utils.mudae_views import TimedDisableView

DIVORCE_CONFIRM_WINDOW_SECONDS = 150  # 2m30s to confirm before the offer expires


class MudaeDivorceConfirmView(TimedDisableView):
    def __init__(
        self, lang: str, user_id: int, user_name: str,
        character_uuid: str, character_name: str, kakera_value: int, guild_id: int
    ):
        super().__init__(timeout=DIVORCE_CONFIRM_WINDOW_SECONDS)
        self.lang = lang
        self.user_id = user_id
        self.user_name = user_name
        self.character_uuid = character_uuid
        self.character_name = character_name
        self.kakera_value = kakera_value
        self.guild_id = guild_id
        self.confirm_button.label = text('mudae_divorce_confirm_button', lang)

    async def interaction_check(self, interaction: nextcord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                text('mudae_divorce_not_for_you_error', self.lang), ephemeral=True
            )
            return False
        return True

    @nextcord.ui.button(label="Confirm", style=nextcord.ButtonStyle.danger)
    async def confirm_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        # Re-verify in case the character was given away since the offer was made.
        current_owner = get_character_owner(self.character_uuid, self.guild_id)
        if current_owner != self.user_id:
            button.disabled = True
            self.stop()
            await interaction.response.edit_message(
                content=text('mudae_divorce_no_longer_valid', self.lang), view=self
            )
            return

        refund = divorce_character(self.character_uuid, self.user_id, self.guild_id, self.kakera_value)

        button.disabled = True
        self.stop()

        success_message = text('mudae_divorce_success', self.lang) \
            .replace('%character%', self.character_name) \
            .replace('%user%', self.user_name) \
            .replace('%kakera_emoji%', config.get('default-mudae-emoji')) \
            .replace('%kakera%', str(refund))
        await interaction.response.edit_message(content=success_message, view=self)


async def _send_divorce_confirmation(lang: str, user: nextcord.abc.User, character_query: str, guild_id: int, send):
    character = find_owned_character(user.id, guild_id, character_query)
    if character is None:
        await send(
            text('mudae_divorce_not_owned_error', lang).replace('%query%', character_query),
            ephemeral=True
        )
        return None

    view = MudaeDivorceConfirmView(
        lang, user.id, user.display_name,
        character["uuid"], character["name"], character["kakera_value"], guild_id
    )
    prompt = text('mudae_divorce_prompt', lang) \
        .replace('%user%', user.mention) \
        .replace('%character%', character["name"])

    sent = await send(prompt, view=view)
    if sent is not None:
        view.bind_message(sent)
    return view


async def mudae_divorce_text(lang: str, message: nextcord.Message):
    character_query = message.content.strip()
    if not character_query:
        await message.reply(text('mudae_divorce_usage_error', lang), mention_author=False)
        return

    async def send(content, **kwargs):
        kwargs.pop('ephemeral', None)
        return await message.reply(content, mention_author=False, **kwargs)

    await _send_divorce_confirmation(lang, message.author, character_query, message.guild.id, send)


async def mudae_divorce_slash(lang: str, interaction: nextcord.Interaction, character: str):
    async def send(content, **kwargs):
        await interaction.response.send_message(content, **kwargs)
        return None

    view = await _send_divorce_confirmation(lang, interaction.user, character, interaction.guild_id, send)
    if view is not None:
        view.bind_interaction(interaction)


info = {
    "divorce": {
        "category": "mudae",
        "aliases": ["release"],
        "hidden_aliases": [],
        "available": ["slash_command", "text_command"],
        "dm_available": False,
        "visibility": "everyone",
        "user_permissions": [],
        "name": "divorce_name",
        "desc": "divorce_desc",
        "args": [
            {
                "name": "divorce_character_arg_name",
                "desc": "divorce_character_arg_desc",
                "required": True,
                "autocomplete": True,
            },
        ]
    },
}

cmd = CmdLocale(list(info.keys())[0], get_commands_locales(info))


class MudaeDivorceCog(commands.Cog):
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
    async def divorce_command(
        self, interaction: nextcord.Interaction,
        character: str = get_slash_option(cmd.arg(0)),
    ):
        await mudae_divorce_slash(get_lang(interaction), interaction, character)

    @divorce_command.on_autocomplete("character")
    async def on_character_autocomplete(self, interaction: nextcord.Interaction, character: str):
        await interaction.response.send_autocomplete(await self.character_autocomplete(interaction, character))


def setup(bot: commands.Bot):
    bot.add_cog(MudaeDivorceCog(bot))


@checks.guild_only()
async def _message_handler(bot, message: nextcord.Message, lang: str, prefix_str: str):
    await mudae_divorce_text(lang, message)
