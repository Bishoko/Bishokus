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

from utils.get_first_attachment import get_first_image
from PIL import Image, ImageSequence, ImageFile, UnidentifiedImageError
from types import NoneType
import io
import os

OVERLAY_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "medias", "zamn.png")
INPUT_SIZE = (250, 359)
PASTE_POSITION = (255, 72)


async def _zamn(image_bytes: bytes) -> nextcord.File:
    # Open input image (may be animated GIF)
    try:
        input_img = Image.open(io.BytesIO(image_bytes))
    except UnidentifiedImageError:
        # Fallback: try incremental parser
        parser = ImageFile.Parser()
        try:
            parser.feed(image_bytes)
            input_img = parser.close()
        except Exception as e:
            log.exception(e, f"Parser failed. First 32 bytes: {image_bytes[:32]!r}")
            raise UnidentifiedImageError("cannot identify image file")

    # Load the zamn overlay
    overlay_img = Image.open(OVERLAY_PATH).convert("RGBA")

    # Handle animated GIFs
    if getattr(input_img, "is_animated", False):
        frames_rgba = []
        durations = []
        for frame in ImageSequence.Iterator(input_img):
            # Convert frame to RGBA and resize
            f = frame.convert("RGBA").resize(INPUT_SIZE, Image.LANCZOS)
            base = overlay_img.copy()
            base.paste(f, PASTE_POSITION, f)
            frames_rgba.append(base)
            durations.append(frame.info.get('duration', input_img.info.get('duration', 100)))

        # Helper to save frames and return BytesIO
        def _save_frames(frames, durations_list, loop):
            pil_frames = [f.convert('P', palette=Image.ADAPTIVE) for f in frames]
            out = io.BytesIO()
            pil_frames[0].save(
                out,
                format='GIF',
                save_all=True,
                append_images=pil_frames[1:],
                loop=loop,
                duration=durations_list,
                optimize=True,
                disposal=2,
            )
            out.seek(0)
            return out

        MAX_BYTES = 8 * 1024 * 1024  # 8 MB Discord limit for non-Nitro
        loop_val = input_img.info.get('loop', 0)

        # Try saving at full size first
        output = _save_frames(frames_rgba, durations, loop_val)
        if output.getbuffer().nbytes <= MAX_BYTES:
            return nextcord.File(output, filename="zamn.gif")

        # Try progressively downscaling
        w, h = frames_rgba[0].size
        for scale in (0.9, 0.8, 0.7, 0.6, 0.5):
            new_size = (max(1, int(w * scale)), max(1, int(h * scale)))
            frames_scaled = [f.resize(new_size, Image.LANCZOS) for f in frames_rgba]
            output = _save_frames(frames_scaled, durations, loop_val)
            if output.getbuffer().nbytes <= MAX_BYTES:
                return nextcord.File(output, filename="zamn.gif")

        # Try reducing frame count (sample frames) and smaller scale
        for sample in (2, 3):
            frames_sampled = frames_rgba[::sample]
            durations_sampled = [sum(durations[i:i + sample]) for i in range(0, len(durations), sample)]
            frames_small = [f.resize((max(1, int(w * 0.5)), max(1, int(h * 0.5))), Image.LANCZOS) for f in frames_sampled]
            output = _save_frames(frames_small, durations_sampled, loop_val)
            if output.getbuffer().nbytes <= MAX_BYTES:
                return nextcord.File(output, filename="zamn.gif")

        # If still too large, raise informative error
        raise Exception("Processed GIF is too large to send after optimization")

    # Static image path (single-frame)
    input_rgba = input_img.convert("RGBA").resize(INPUT_SIZE, Image.LANCZOS)
    overlay = overlay_img.copy()
    overlay.paste(input_rgba, PASTE_POSITION, input_rgba)

    output = io.BytesIO()
    overlay.save(output, format="PNG")
    output.seek(0)

    return nextcord.File(output, filename="zamn.png")


async def zamn_text(lang: str, message: nextcord.Message):
    image_bytes = await get_first_image(message)

    if image_bytes is None:
        await message.reply(text('zamn_no_image_error', lang), mention_author=False)
        return

    try:
        file = await _zamn(image_bytes)
    except Exception as e:
        log.exception(e)
        await message.reply(text('zamn_processing_error', lang), mention_author=False)
        return

    await message.reply(
        file=file,
        mention_author=False
    )


async def zamn_slash(lang: str, interaction: nextcord.Interaction, image: nextcord.Attachment | NoneType = None, link: str = ""):
    await interaction.response.defer()

    image_bytes = None
    if image:
        image_bytes = await image.read()
    elif link:
        image_bytes = await get_first_image(link)
        
    if not image_bytes:
        await interaction.followup.send(text('zamn_missing_argument_error', lang))
        return
    
    try:
        file = await _zamn(image_bytes)
    except Exception as e:
        log.exception(e)
        await interaction.followup.send(text('zamn_processing_error', lang))
        return

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
                "name": "zamn_image_arg_name",
                "desc": "zamn_image_arg_desc",
                "required": False,
            },
            {
                "name": "zamn_link_arg_name",
                "desc": "zamn_link_arg_desc",
                "required": False,
            },
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
        link: str = get_slash_option(cmd.arg(1)),
    ):
        await zamn_slash(get_lang(interaction), interaction, image, link)


def setup(bot: commands.Bot):
    bot.add_cog(ZamnCog(bot))

# Text command handler wrapper that adapts to message handler signature
async def _message_handler(bot, message: nextcord.Message, lang: str, guild_prefix: str):
    await zamn_text(lang, message)
