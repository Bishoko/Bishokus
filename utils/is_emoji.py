import emoji
from nextcord.ext.commands.core import T

def is_emoji(value: str) -> bool:
    """
    Check if a given character is an emoji.

    Args:
        value (str): A character to check.

    Returns:
        bool: True if the value is an emoji, False otherwise.
    """
    value = str(value).strip()
    if not value:
        return False

    matches = emoji.emoji_list(value)
    return (
        len(matches) == 1
        and matches[0]["match_start"] == 0
        and matches[0]["match_end"] == len(value)
    )

if __name__ == "__main__":
    while True:
        test = input("Enter a character to check (or 'q' to quit): ")
        if test.lower() == 'q':
            break
        print(is_emoji(test))
