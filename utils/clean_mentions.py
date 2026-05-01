import re

def clean_mentions(text: str) -> str:
    """Normalize input strings to avoid user injection that makes the bot mention users/roles/everyone."""
    
    # regex to find user and role mentions (<@ID>)
    mentions: list[str] = re.findall(r'<@\d+>', text)
    for mention in mentions:
        text = text.replace(mention, mention.replace('@', '@​'))
    
    # Remove everyone/here mentions
    text = text.replace('@everyone', '@​everyone').replace('@here', '@​here')
    return text
