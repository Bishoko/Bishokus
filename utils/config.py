import json
import os


def get_config():
    with open("config/config.json", "r", encoding='utf-8') as f:
        config = json.load(f)

    # Override sensitive values with environment variables if present
    if os.getenv("BOT_TOKEN"):
        if "tokens" not in config:
            config["tokens"] = {}
        config["tokens"]["main"] = os.getenv("BOT_TOKEN")

    if os.getenv("TEST_BOT_TOKEN"):
        if "tokens" not in config:
            config["tokens"] = {}
        config["tokens"]["test"] = os.getenv("TEST_BOT_TOKEN")

    if os.getenv("OPENWEATHER_API_KEY"):
        if "api-keys" not in config:
            config["api-keys"] = {}
        config["api-keys"]["openweather"] = os.getenv("OPENWEATHER_API_KEY")

    if os.getenv("BLAGUES_API_KEY"):
        if "api-keys" not in config:
            config["api-keys"] = {}
        config["api-keys"]["blagues"] = os.getenv("BLAGUES_API_KEY")

    return config


config = get_config()
