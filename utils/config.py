import json

def get_config():
    with open("config/config.json", "r", encoding='utf-8') as f:
        config = json.load(f)
    return config

config = get_config()
