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
import subprocess  # nosec B404
import shutil
import asyncio
import tempfile
import math
import json
import io
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
) -> str:
    """
    Convert a video to a GIF, targeting a maximum output file size.

    Args:
        input_path:  Path to the source video (any format ffmpeg supports).
        max_size_mb: Maximum output file size in megabytes (default 15).
        max_fps:     FPS cap, original FPS is used if lower (default 24).
        colors:      Palette size: 64 | 128 | 256. Lower = smaller, less accurate
                     color reproduction (default 128, good balance).

    Returns:
        Path to the generated GIF.

    Raises:
        RuntimeError:      If ffmpeg fails or the minimum width (120px) is exceeded.
    """

    output_path = os.path.splitext(input_path)[0] + ".gif"

    max_bytes = max_size_mb * 1024 * 1024
    palette_path = output_path + ".palette.png"

    # Probe
    probe = _probe(input_path)
    src_w, src_h = probe["width"], probe["height"]
    src_fps = probe["fps"]
    duration = probe["duration"]

    est_full = _estimate_size_bytes(src_w, src_h, min(src_fps, max_fps), duration)
    log.debug(f"Source: {src_w}×{src_h} @ {src_fps:.1f}fps, {duration:.1f}s")
    log.debug(f"Estimated full-res GIF: {est_full / 1024 / 1024:.1f} MB")

    # Pick parameters analytically
    width, fps = _pick_params(src_w, src_h, src_fps, duration, max_bytes, max_fps)
    height = -1  # let ffmpeg compute height to preserve aspect ratio

    est = _estimate_size_bytes(width, round(width * src_h / src_w), fps, duration)
    log.debug(f"Target: {width}px wide @ {fps:.1f}fps → estimated {est / 1024 / 1024:.1f} MB")

    def encode(w: int, fps: float) -> int:
        vf_palette = (
            f"fps={fps:.3f},"
            f"scale={w}:{height}:flags=lanczos,"
            f"palettegen=max_colors={colors}:stats_mode=diff"
        )
        vf_gif = (
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

async def _convert_to_gif(input_filename: str = "", image: bytes | None = None, video: bytes | None = None) -> str:
    if image:
        # If it's already an image, just return it as a file lol it just works
        return nextcord.File(io.BytesIO(image), filename="output.gif")
    elif video:
        # Convert video to GIF using moviepy
        try:
            # Write video bytes to a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
                tmp_file.write(video)
                tmp_path = tmp_file.name
                log.debug(f"Temporary video file created at: {tmp_path}")

            output_path: str = await asyncio.to_thread(_video_to_gif, tmp_path)

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
    # Check message attachments first, then the replied message's attachments
    file = None
    image_bytes = await get_first_image(message)

    try:
        if image_bytes:
            file = await _convert_to_gif(image=image_bytes)
        else:
            video_bytes = await get_first_video(message)
            file = await _convert_to_gif(video=video_bytes)
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

async def gif_slash(lang: str, interaction: nextcord.Interaction, input: nextcord.Attachment):
    await interaction.response.defer()
    file = None

    try:
        # Check message attachments first, then the replied message's attachments
        if input.content_type and input.content_type.startswith("image"):
            image_bytes = await input.read()
            file = await _convert_to_gif(image=image_bytes)
            
        elif input.content_type and input.content_type.startswith("video"):
            video_bytes = await input.read()
            file = await _convert_to_gif(video=video_bytes)

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
            filename=f"{input.filename}_bishokus.gif",
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
                "name": "gif_arg_name",
                "desc": "gif_arg_desc"
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
        attachment: nextcord.Attachment = get_slash_option(cmd.arg(0))
    ):
        await gif_slash(get_lang(interaction), interaction, attachment)


def setup(bot: commands.Bot):
    bot.add_cog(GifCog(bot))

# Text command handler wrapper that adapts to message handler signature
async def _message_handler(bot, message: nextcord.Message, lang: str, guild_prefix: str):
    await gif_text(lang, message)
