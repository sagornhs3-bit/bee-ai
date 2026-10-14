"""
Bee - Memory System
"""

import json
import datetime
from pathlib import Path

MEMORY_FILE = Path(__file__).parent / "bee_memory.json"


def _load():
    if MEMORY_FILE.exists():
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"user_name": "", "facts": {}, "history": []}


def _save(data):
    try:
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[memory save failed: {e}]")


def set_user_name(name: str):
    data = _load()
    data["user_name"] = name.strip()
    _save(data)


def get_user_name() -> str:
    return _load().get("user_name", "")


def remember(key: str, value: str):
    data = _load()
    data["facts"][key.strip()] = value.strip()
    _save(data)


def recall(key: str):
    return _load()["facts"].get(key.strip())


def get_all_facts() -> dict:
    return _load().get("facts", {})


def add_history(user_msg: str, bee_msg: str):
    data = _load()
    entry = {
        "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "user": user_msg[:200],
        "bee": bee_msg[:200],
    }
    data["history"].append(entry)
    data["history"] = data["history"][-30:]
    _save(data)


def get_recent_history(n: int = 5):
    return _load().get("history", [])[-n:]


def build_memory_context() -> str:
    data = _load()
    parts = []
    name = data.get("user_name", "").strip()
    if name:
        parts.append(f"ব্যবহারকারীর নাম: {name}")
    facts = data.get("facts", {})
    if facts:
        parts.append("ব্যবহারকারী সম্পর্কে:")
        for k, v in facts.items():
            parts.append(f"  - {k}: {v}")
    return "\n".join(parts) if parts else ""