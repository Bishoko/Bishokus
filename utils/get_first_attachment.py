import nextcord
import requests
from utils.get_urls import get_urls
from utils.logger import log

IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.avif')

async def get_first_image(message: nextcord.Message) -> bytes | None:
    """
    Retrieves the first image from message attachments or the replied message's attachments.
    Returns the image bytes or None if no image is found.
    """
    attachment = None

    # Check message attachments first
    if message.attachments:
        for att in message.attachments:
            log.debug(f"Checking attachment: {att.filename} with content type {att.content_type}")
            if (att.content_type and att.content_type.startswith("image/")) or (att.filename and att.filename.lower().endswith(IMAGE_EXTENSIONS)):
                attachment = att
                break

    # If no image found, check the replied message's attachments
    if attachment is None and message.reference and isinstance(message.reference.resolved, nextcord.Message):
        ref_msg = message.reference.resolved
        if ref_msg.attachments:
            for att in ref_msg.attachments:
                if (att.content_type and att.content_type.startswith("image/")) or (att.filename and att.filename.lower().endswith(IMAGE_EXTENSIONS)):
                    attachment = att
                    break

    # If no image found, check URLs
    if attachment is None:
        urls = get_urls(message.content)
        for url in urls:
            if url.rsplit('?', 1)[0].lower().endswith(IMAGE_EXTENSIONS):
                attachment = url
                break
    
    # TODO: If no image found, check mentioned members for pfp? (get_user.py)
    
    if attachment is None:
        return None
    
    if isinstance(attachment, nextcord.Attachment):
        image = await attachment.read()
    else:
        # Get the image from the URL
        try:
            response = requests.get(attachment, timeout=5)
            response.raise_for_status()
            image = response.content
        except requests.RequestException as e:
            log.error(f"Failed to fetch image from URL {attachment}: {e}")
            return None
    
    return image
