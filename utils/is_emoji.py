from emoji import UNICODE_EMOJI

def is_emoji(character: str):
    """
    Check if a given character is an emoji.

    Args:
        character (str): A single character to check.

    Returns:
        bool: True if the character is an emoji, False otherwise.
    """
    return str(character).strip() in UNICODE_EMOJI['en']