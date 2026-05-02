import re

def get_urls(text: str) -> list[str]:
    """Extracts URLs from the given text using a regular expression pattern.
    Supports both http and https URLs.
    
    Args:
        text (str): The text to extract URLs from.

    Returns:
        list[str]: A list of URLs found in the text.
    """
    url_pattern = re.compile(r'https?://\S+')
    return url_pattern.findall(text)
