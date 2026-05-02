import emoji

def is_emoji(value: str) -> bool:
    """
    Check if a given value is a single emoji sequence.

    Args:
        value (str): The value to check.

    Returns:
        bool: True if the value is an emoji, False otherwise.
    """
    value = str(value).strip()
    if not value:
        return False
    return emoji.is_emoji(value)

if __name__ == "__main__":
    while True:
        test = input("Enter a character to check (or 'q' to quit): ")
        if test.lower() == 'q':
            break
        print(is_emoji(test))
