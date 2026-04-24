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

from utils.get_first_image import get_first_image
from PIL import Image
import io
import os

OVERLAY_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "medias", "open_to_work.png")
SIZE = (720, 720)


async def _open_to_work(image_bytes: bytes) -> nextcord.File:
    # Squish input image to a 720x720 square
    avatar_img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    avatar_img = avatar_img.resize(SIZE, Image.LANCZOS)

    # Load overlay and resize it to match the output size
    overlay_img = Image.open(OVERLAY_PATH).convert("RGBA")
    overlay_img = overlay_img.resize(SIZE, Image.LANCZOS)

    # Paste the overlay on top of the input image using its alpha channel as mask
    avatar_img.paste(overlay_img, (0, 0), overlay_img)

    output = io.BytesIO()
    avatar_img.save(output, format="PNG")
    output.seek(0)

    return nextcord.File(output, filename="open_to_work.png")


async def open_to_work_text(lang: str, message: nextcord.Message):
    # Check message attachments first, then the replied message's attachments
    image_bytes = await get_first_image(message)

    if image_bytes is None:
        await message.reply(text('open_to_work_no_image_error', lang), mention_author=False)
        return

    file = await _open_to_work(image_bytes)

    await message.reply(
        file=file,
        mention_author=False
    )


async def open_to_work_slash(lang: str, interaction: nextcord.Interaction, image: nextcord.Attachment):
    await interaction.response.defer()
    image_bytes = await image.read()
    file = await _open_to_work(image_bytes)

    await interaction.followup.send(file=file)


info = {
    "open_to_work": {
        "category": "utilities",
        "aliases": ["otw", "opentowork", "linkedin"],
        "hidden_aliases": ["linkedify"],
        "available": ["slash_command", "text_command"],
        "visibility": "everyone",
        "user_permissions": [],
        "name": "open_to_work_name",
        "desc": "open_to_work_desc",
        "args": [
            {
                "name": "open_to_work_arg_name",
                "desc": "open_to_work_arg_desc",
            }
        ]
    }
}

cmd = CmdLocale(list(info.keys())[0], get_commands_locales(info))


class OpenToWorkCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @check_ban()
    @slash_command(
        name=cmd.name,
        description=cmd.description,
        name_localizations=cmd.name_localizations,
        description_localizations=cmd.description_localizations
    )
    async def open_to_work_command(self, interaction: nextcord.Interaction,
        image: nextcord.Attachment = get_slash_option(cmd.arg(0)),
    ):
        await open_to_work_slash(get_lang(interaction), interaction, image)


def setup(bot: commands.Bot):
    bot.add_cog(OpenToWorkCog(bot))

# Text command handler wrapper that adapts to message handler signature
async def _message_handler(bot, message: nextcord.Message, lang: str, guild_prefix: str):
    await open_to_work_text(lang, message)
