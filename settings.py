"""Bee - Settings manager (language preference)"""

import json
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / "config.json"


def get_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(data):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_reply_language():
    """Returns 'auto' | 'bn' | 'en'"""
    try:
        return get_config().get("reply_language", "auto")
    except Exception:
        return "auto"


def set_reply_language(lang):
    """lang = 'auto' | 'bn' | 'en'"""
    if lang not in ("auto", "bn", "en"):
        return False
    try:
        data = get_config()
        data["reply_language"] = lang
        save_config(data)
        return True
    except Exception:
        return False