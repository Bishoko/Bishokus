import nextcord
import requests
from utils.get_urls import get_urls


async def get_first_image(message: nextcord.Message) -> bytes | None:
    """
    Retrieves the first image from message attachments or the replied message's attachments.
    Returns the image bytes or None if no image is found.
    """
    attachment = None

    # Check message attachments first
    if message.attachments:
        for att in message.attachments:
            if att.content_type and att.content_type.startswith("image/"):
                attachment = att
                break

    # If no image found, check the replied message's attachments
    if attachment is None and message.reference and isinstance(message.reference.resolved, nextcord.Message):
        ref_msg = message.reference.resolved
        if ref_msg.attachments:
            for att in ref_msg.attachments:
                if att.content_type and att.content_type.startswith("image/"):
                    attachment = att
                    break

    # If no image found, check URLs
    if attachment is None:
        urls = get_urls(message.content.lower())
        for url in urls:
            if url.rsplit('?', 1)[0].endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp', '.avif')):
                attachment = url
                break
    
    # TODO: If no image found, check mentioned members for pfp? (get_user.py)
    
    if attachment is None:
        return None
    
    if isinstance(attachment, nextcord.Attachment):
        image = await attachment.read()
    else:
        # Get the image from the URL
        response = requests.get(attachment, timeout=5)
        image = response.content
    
    return image
