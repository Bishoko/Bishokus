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

import io
import os
from PIL import Image

from utils.get_first_attachment import get_first_image

OVERLAY_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "medias", "zamn.png")
INPUT_SIZE = (250, 359)
PASTE_POSITION = (255, 72)


async def _zamn(image_bytes: bytes) -> nextcord.File:
    # Resize input image to the required dimensions
    input_img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    input_img = input_img.resize(INPUT_SIZE, Image.LANCZOS)

    # Load the zamn overlay
    overlay_img = Image.open(OVERLAY_PATH).convert("RGBA")

    # Paste the input image on top of the overlay using its alpha channel as mask
    overlay_img.paste(input_img, PASTE_POSITION, input_img)

    output = io.BytesIO()
    overlay_img.save(output, format="PNG")
    output.seek(0)

    return nextcord.File(output, filename="zamn.png")


async def zamn_text(lang: str, message: nextcord.Message):
    image_bytes = await get_first_image(message)

    if image_bytes is None:
        await message.reply(text('zamn_no_image_error', lang), mention_author=False)
        return

    file = await _zamn(image_bytes)

    await message.reply(
        file=file,
        mention_author=False
    )


async def zamn_slash(lang: str, interaction: nextcord.Interaction, image: nextcord.Attachment):
    await interaction.response.defer()
    image_bytes = await image.read()
    file = await _zamn(image_bytes)

    await interaction.followup.send(file=file)


info = {
    "zamn": {
        "category": "fun",
        "aliases": ["zamnify"],
        "hidden_aliases": [],
        "available": ["slash_command", "text_command"],
        "visibility": "everyone",
        "user_permissions": [],
        "name": "zamn_name",
        "desc": "zamn_desc",
        "args": [
            {
                "name": "zamn_arg_name",
                "desc": "zamn_arg_desc",
            }
        ]
    }
}

cmd = CmdLocale(list(info.keys())[0], get_commands_locales(info))


class ZamnCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @check_ban()
    @slash_command(
        name=cmd.name,
        description=cmd.description,
        name_localizations=cmd.name_localizations,
        description_localizations=cmd.description_localizations
    )
    async def zamn_command(self, interaction: nextcord.Interaction,
        image: nextcord.Attachment = get_slash_option(cmd.arg(0)),
    ):
        await zamn_slash(get_lang(interaction), interaction, image)


def setup(bot: commands.Bot):
    bot.add_cog(ZamnCog(bot))

# Text command handler wrapper that adapts to message handler signature
async def _message_handler(bot, message: nextcord.Message, lang: str, guild_prefix: str):
    await zamn_text(lang, message)
