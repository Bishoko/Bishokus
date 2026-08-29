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

from utils.get_first_attachment import get_first_image, get_first_video
from utils.vip import is_vip
from types import NoneType
from pathlib import Path
from PIL import Image
import subprocess  # nosec B404
import shutil
import asyncio
import tempfile
import random
import string
import math
import json
import os

# Empirically measured bytes/pixel for palettegen+paletteuse+bayer GIFs.
# Calibrated from real encodes; used to predict output size before encoding.
_BYTES_PER_PIXEL = 0.22
FFMPEG_PATH = shutil.which("ffmpeg") or "ffmpeg"
FFPROBE_PATH = shutil.which("ffprobe") or "ffprobe"

def _probe(input_path: str) -> dict:
    """Return a dict with duration, fps, width, height from ffprobe."""
    result = subprocess.run(  # nosec 602
        [
            FFPROBE_PATH, "-v", "quiet",
            "-print_format", "json",
            "-show_streams", "-show_format",
            input_path,
        ],
        capture_output=True, text=True, check=True,
    )
    info = json.loads(result.stdout)
    vs = next(s for s in info["streams"] if s["codec_type"] == "video")
    num, den = vs["r_frame_rate"].split("/")
    return {
        "duration": float(info["format"]["duration"]),
        "fps": float(num) / float(den),
        "width": int(vs["width"]),
        "height": int(vs["height"]),
    }

def _estimate_size_bytes(width: int, height: int, fps: float, duration: float) -> float:
    """Predict GIF output size in bytes from pixel count alone."""
    return width * height * fps * duration * _BYTES_PER_PIXEL

def _pick_params(
    src_w: int, src_h: int, src_fps: float, duration: float,
    max_bytes: float, max_fps: float,
) -> tuple[int, float]:
    """
    Return (width, fps) that should land just under max_bytes.

    Strategy:
      - Cap FPS at max_fps (default 24). Don't lower it, resolution is cheaper and I like fluidity.
      - Solve analytically for the width that hits the target in one shot.
    """
    fps = min(src_fps, max_fps)
    ratio = src_h / src_w

    # Solve: w * (w*ratio) * fps * duration * bpp = max_bytes ->  w = sqrt(...)
    target_w = math.sqrt(max_bytes / (ratio * fps * duration * _BYTES_PER_PIXEL))

    # Apply a small safety margin (0.85) so we land under, not over
    target_w = int(target_w * 0.85)

    # Clamp: don't exceed source width, don't go below 120px
    target_w = max(120, min(target_w, src_w))

    # Round to nearest even number (required by many codecs/filters)
    target_w = (target_w // 2) * 2

    return target_w, fps

def _video_to_gif(
    input_path: str,
    max_size_mb: float = 15.0,
    max_fps: float = 24.0,
    colors: int = 128,
    speedup: int = 0,
) -> str:
    """
    Convert a video to a GIF, targeting a maximum output file size.

    Args:
        input_path:  Path to the source video (any format ffmpeg supports).
        max_size_mb: Maximum output file size in megabytes (default 15).
        max_fps:     FPS cap, original FPS is used if lower (default 24).
        colors:      Palette size: 64 | 128 | 256. Lower = smaller, less accurate
                     color reproduction (default 128, good balance).
        speedup:     Speed multiplier as a percentage (0, 25, 50, 75, 100, 125, 150).
                     0% = normal speed, 50% = 1.5x speed (recommended), 75% = 1.75x, 100% = 2x, 125 = x2.25, 150 = x2.5.

    Returns:
        Path to the generated GIF.

    Raises:
        RuntimeError:      If ffmpeg fails or the minimum width (120px) is exceeded.
    """

    output_path = os.path.splitext(input_path)[0] + ".gif"

    max_bytes = max_size_mb * 1024 * 1024
    palette_path = output_path + ".palette.png"

    speedup_multiplier = 1 + (speedup / 100)

    # Probe
    probe = _probe(input_path)
    src_w, src_h = probe["width"], probe["height"]
    src_fps = probe["fps"]
    duration = probe["duration"] / speedup_multiplier

    est_full = _estimate_size_bytes(src_w, src_h, min(src_fps, max_fps), duration)
    log.debug(f"Source: {src_w}×{src_h} @ {src_fps:.1f}fps, {duration:.1f}s")
    log.debug(f"Estimated full-res GIF: {est_full / 1024 / 1024:.1f} MB")

    # Pick parameters analytically
    width, fps = _pick_params(src_w, src_h, src_fps, duration, max_bytes, max_fps)
    height = -1  # let ffmpeg compute height to preserve aspect ratio

    est = _estimate_size_bytes(width, round(width * src_h / src_w), fps, duration)
    log.debug(f"Target: {width}px wide @ {fps:.1f}fps → estimated {est / 1024 / 1024:.1f} MB")

    def encode(w: int, fps: float) -> int:
        setpts_filter = f"setpts=PTS/{speedup_multiplier}," if speedup_multiplier > 1 else ""

        vf_palette = (
            f"{setpts_filter}"
            f"fps={fps:.3f},"
            f"scale={w}:{height}:flags=lanczos,"
            f"palettegen=max_colors={colors}:stats_mode=diff"
        )
        vf_gif = (
            f"{setpts_filter}"
            f"fps={fps:.3f},"
            f"scale={w}:{height}:flags=lanczos[x];"
            f"[x][1:v]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle"
        )

        # generate palette (single frame, very fast)
        subprocess.run(  # nosec 602
            [FFMPEG_PATH, "-y", "-i", input_path,
             "-vf", vf_palette, "-frames:v", "1", palette_path],
            capture_output=True, check=True,
        )

        # encode GIF
        subprocess.run(  # nosec 602
            [FFMPEG_PATH, "-y",
             "-i", input_path, "-i", palette_path,
             "-filter_complex", vf_gif,
             output_path],
            capture_output=True, check=True,
        )

        return os.path.getsize(output_path)

    # Encode
    try:
        size = encode(width, fps)
        log.debug(f"Encoded: {size / 1024 / 1024:.2f} MB")

        # Single retry if over target (high-entropy content)
        if size > max_bytes:
            # Recalibrate bpp from this encode and solve again
            actual_h = round(width * src_h / src_w)
            actual_bpp = size / (width * actual_h * fps * duration)
            log.debug(f"Over target, recalibrating (actual bpp={actual_bpp:.3f}), retrying…")

            ratio = src_h / src_w
            new_w = math.sqrt(max_bytes / (ratio * fps * duration * actual_bpp))
            new_w = max(120, int(new_w * 0.90))
            new_w = (new_w // 2) * 2

            if new_w < 120:
                log.debug(f"Cannot reach {max_size_mb} MB: content is too complex :/")
            else:
                size = encode(new_w, fps)
                log.debug(f"Retry {new_w}px → {size / 1024 / 1024:.2f} MB")

        result_mb = size / 1024 / 1024
        status = "" if size <= max_bytes else "[over target]"
        log.debug(f"{status} GIF saved: {output_path} ({result_mb:.2f} MB)")
        if size >= max_bytes:
            raise ValueError("content is too complex")
        return output_path

    finally:
        if os.path.isfile(palette_path):
            os.remove(palette_path)


def _image_to_gif(input_path: str) -> str:
    """
    Convert an image to a single-frame GIF.
 
    Args:
        input_path: Path to the source image.
 
    Returns:
        Path to the saved GIF file.
    """
    src = Path(input_path)
    dst = src.with_suffix('.gif')
 
    with Image.open(src) as img:
        img = img.convert('RGBA')
        alpha = img.getchannel('A').point(lambda a: 255 if a == 0 else 0)
        frame = img.convert('RGB').convert('P', palette=Image.Palette.ADAPTIVE, colors=255)
        frame.paste(255, mask=alpha)
        frame.save(dst, format='GIF', save_all=True, transparency=255)
 
    return str(dst)


def _parse_speedup(speedup_input: str, user_id: int) -> int | None:
    """
    Parse speedup input and return the speedup percentage (additive).
    Accepts formats like: "1.5", "1.5x", "150%"
    Returns the speedup amount (e.g., 50 for 150% total speed).
    Returns None if parsing fails.
    """
    if not speedup_input:
        return None

    speedup_input = speedup_input.strip().lower()

    try:
        # Remove 'x' if present
        if speedup_input.endswith('x'):
            speedup_input = speedup_input[:-1]

        # Remove '%' if present
        if speedup_input.endswith('%'):
            speedup_input = speedup_input[:-1]

        speedup_value = float(speedup_input)

        # If value > 10, assume it's a percentage (e.g., 150)
        if speedup_value > 10:
            total_percent = speedup_value
        else:
            # Assume it's a multiplier (e.g., 1.5)
            total_percent = speedup_value * 100

        # Convert total percent to speedup (additive)
        speedup = int(total_percent - 100)

        # Clamp to reasonable values
        if is_vip(user_id):
            log.debug(f"User is VIP, skipping gif speedup limits for: {speedup}")
            return speedup
        return max(0, min(speedup, 150))
    except (ValueError, AttributeError):
        return None


async def _convert_to_gif(input_filename: str = "", image: bytes | None = None, video: bytes | None = None, speedup: int = 0) -> str | None:
    original_extension = input_filename.split('.')[-1].lower()
    output_path: str = ""
    
    try:
        if image:
            # Write image bytes to a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=original_extension or ".png") as tmp_file:
                tmp_file.write(image)
                tmp_path = tmp_file.name
                log.debug(f"Temporary image file created at: {tmp_path}")
                
            output_path = await asyncio.to_thread(_image_to_gif, tmp_path)
            
            try:
                return output_path
            finally:
                try:
                    os.unlink(tmp_path)
                except Exception as e:
                    log.exception(e, "Failed to delete temporary video file")
            
            
        elif video:
            # Write video bytes to a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=original_extension or ".mp4") as tmp_file:
                tmp_file.write(video)
                tmp_path = tmp_file.name
                log.debug(f"Temporary video file created at: {tmp_path}")

            output_path = await asyncio.to_thread(_video_to_gif, tmp_path, speedup=speedup)

            try:
                return output_path
            finally:
                try:
                    os.unlink(tmp_path)
                except Exception as e:
                    log.exception(e, "Failed to delete temporary video file")
    except Exception as e:
        log.exception(e, "Failed to convert video to GIF")
        raise


async def gif_text(lang: str, message: nextcord.Message):
    # Parse speedup from message content
    speedup = 0
    words = message.content.split()
    for word in words:
        parsed = _parse_speedup(word, message.author.id)
        if parsed is not None:
            speedup = parsed
            break

    # Check message attachments first, then the replied message's attachments
    file = None
    image_bytes = await get_first_image(message)

    try:
        if image_bytes:
            file = await _convert_to_gif(image=image_bytes, speedup=speedup)
        else:
            video_bytes = await get_first_video(message)
            file = await _convert_to_gif(video=video_bytes, speedup=speedup)
    except ValueError:
        await message.reply(
            text("gif_error_too_complex", lang),
            mention_author=False
        )
        return
    except Exception as e:
        log.exception(e, "Unknown error occured while converting an image or video to gif")
        await message.reply(
            text("gif_unknown_error", lang),
            mention_author=False
        )
        return
        

    if not file:
        await message.reply(
            text("gif_error_missing_file", lang),
            mention_author=False
        )
        return
        
    await message.reply(
        file=nextcord.File(
            file,
            filename="attachment_bishokus.gif",
            force_close=True
        ),
        mention_author=False
    )
    
    try:
        os.unlink(file)
    except Exception as e:
        log.exception(e, "Failed to delete temporary video output file")
    return

async def gif_slash(lang: str, interaction: nextcord.Interaction, attachment: nextcord.Attachment | NoneType, link: str = "", speedup: int = 0):
    if not attachment and not link:
        await interaction.response.send_message(text('gif_error_missing_file', lang))
        return

    await interaction.response.defer()
    file = None
    original_filename = attachment.filename if attachment else ''.join(random.choices(string.ascii_letters + string.digits, k=8))  # TODO: get actual original filename

    try:
        # Check message attachments first, then the replied message's attachments
        if attachment and attachment.content_type and attachment.content_type.startswith("image"):
            image_bytes = await attachment.read()
            file = await _convert_to_gif(attachment.filename, image=image_bytes, speedup=speedup)

        elif attachment and attachment.content_type and attachment.content_type.startswith("video"):
            video_bytes = await attachment.read()
            file = await _convert_to_gif(attachment.filename, video=video_bytes, speedup=speedup)

        # Check for the provided link
        if link:
            image_bytes = await get_first_image(link)
            if image_bytes:
                file = await _convert_to_gif(original_filename, image=image_bytes, speedup=speedup)

            video_bytes = await get_first_video(link)
            if video_bytes:
                file = await _convert_to_gif(original_filename, video=video_bytes, speedup=speedup)

        else:
            await interaction.followup.send(
                text("gif_invalid_attachment", lang),
                ephemeral=True
            )
            return
    except ValueError:
        await interaction.followup.send(
            text("gif_error_too_complex", lang)
        )
        return
    except Exception as e:
        log.exception(e, "Unknown error occured while converting an image or video to gif")
        await interaction.followup.send(
            text("gif_unknown_error", lang)
        )
        return

    if not file:
        await interaction.followup.send(
            text("gif_unknown_error", lang)
        )
        return
    
    await interaction.followup.send(
        file=nextcord.File(
            file,
            filename=f"{original_filename}_bishokus.gif",
            force_close=True
        ),
        ephemeral=False
    )
    try:
        os.unlink(file)
    except Exception as e:
        log.exception(e, "Failed to delete temporary video output file")
    return


info = {
    "gif": {
        "category": "utilities",
        "aliases": ["to_gif"],
        "hidden_aliases": [
            "togif", "convert_to_gif", "convertgif", "convert_gif",
            "gifvideo", "videogif", "videotogif", "video_to_gif",
            "gifimage", "imagegif", "imagetogif", "image_to_gif"
        ],
        "available": ["slash_command", "text_command"],
        "visibility": "everyone",
        "user_permissions": [],
        "name": "gif_name",
        "desc": "gif_desc",
        "args": [
            {
                "name": "gif_media_arg_name",
                "desc": "gif_media_arg_desc",
                "required": False,
            },
            {
                "name": "gif_link_arg_name",
                "desc": "gif_link_arg_desc",
                "required": False,
            },
            {
                "name": "gif_speedup_arg_name",
                "desc": "gif_speedup_arg_desc",
                "choices": {
                    "100% (Normal)": 0,
                    "125%": 25,
                    "150%": 50,
                    "175%": 75,
                    "200% (Recommended)": 100,
                    "225%": 125,
                    "250%": 150,
                },
                "default": 0,
                "required": False,
            }
        ]
    }
}

cmd = CmdLocale(list(info.keys())[0], get_commands_locales(info))

class GifCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @check_ban()
    @slash_command(
        name=cmd.name,
        description=cmd.description,
        name_localizations=cmd.name_localizations,
        description_localizations=cmd.description_localizations
    )
    async def gif_command(self, interaction: nextcord.Interaction,
        attachment: nextcord.Attachment = get_slash_option(cmd.arg(0)),
        link: str = get_slash_option(cmd.arg(1)),
        speedup: int = get_slash_option(cmd.arg(2)),
    ):
        await gif_slash(get_lang(interaction), interaction, attachment, link, speedup)


def setup(bot: commands.Bot):
    bot.add_cog(GifCog(bot))

# Text command handler wrapper that adapts to message handler signature
async def _message_handler(bot, message: nextcord.Message, lang: str, guild_prefix: str):
    await gif_text(lang, message)
