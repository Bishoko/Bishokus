import nextcord
import requests
from utils.get_urls import get_urls
from utils.logger import log


async def get_first_attachment(message: nextcord.Message | str, type: str = "image", allowed_extensions: tuple = ()) -> bytes | None:
    """
    Retrieves the first attachment from message attachments or the replied message's attachments.
    Returns the attachment bytes or None if no attachment is found.
    """
    attachment = None

    if isinstance(message, nextcord.Message):
        # Check message attachments first
        if message.attachments:
            for att in message.attachments:
                log.debug(f"Checking attachment: {att.filename} with content type {att.content_type}")
                if (att.content_type and att.content_type.startswith(f"{type}/")) or (att.filename and att.filename.lower().endswith(allowed_extensions)):
                    attachment = att
                    break
    
        # If no attachment found, check the replied message's attachments
        if attachment is None and message.reference and isinstance(message.reference.resolved, nextcord.Message):
            ref_msg = message.reference.resolved
            if ref_msg.attachments:
                for att in ref_msg.attachments:
                    if (att.content_type and att.content_type.startswith(f"{type}/")) or (att.filename and att.filename.lower().endswith(allowed_extensions)):
                        attachment = att
                        break

    # If no attachment found, check URLs
    if attachment is None:
        urls = get_urls(message.content if isinstance(message, nextcord.Message) else message)
        for url in urls:
            if url.rsplit('?', 1)[0].lower().endswith(allowed_extensions):
                attachment = url
                break

    
    if attachment is None:
        return None
    
    if isinstance(attachment, nextcord.Attachment):
        attachment = await attachment.read()
    else:
        # Get the image from the URL
        try:
            response = requests.get(attachment, timeout=5)
            response.raise_for_status()
            attachment = response.content
        except requests.RequestException as e:
            log.error(f"Failed to fetch attachment from URL {attachment}: {e}")
            return None
    
    return attachment

async def get_first_image(message: nextcord.Message | str) -> bytes | None:
    # TODO: If no image found, check mentioned members for pfp? (get_user.py)
    IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.avif')
    return await get_first_attachment(message, type="image", allowed_extensions=IMAGE_EXTENSIONS)

async def get_first_video(message: nextcord.Message | str) -> bytes | None:
    VIDEO_EXTENSIONS = ('.mp4', '.webm', '.wmv', '.avi', '.mov', '.mkv', '.flv')
    return await get_first_attachment(message, type="video", allowed_extensions=VIDEO_EXTENSIONS)
