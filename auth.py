"""Bee - Simple authentication system"""

import hashlib
import json
from pathlib import Path

AUTH_FILE = Path(__file__).parent / "auth.json"

DEFAULT_USER = "admin"
DEFAULT_PASS = "bee2026"


def _hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _load():
    if AUTH_FILE.exists():
        try:
            return json.loads(AUTH_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    data = {
        "users": {
            DEFAULT_USER: {
                "password": _hash(DEFAULT_PASS),
                "role": "admin",
            }
        }
    }
    _save(data)
    return data


def _save(data):
    AUTH_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def verify_login(username, password):
    data = _load()
    user = data["users"].get(username)
    if not user:
        return False
    return user["password"] == _hash(password)


def add_user(username, password, role="user"):
    data = _load()
    data["users"][username] = {
        "password": _hash(password),
        "role": role,
    }
    _save(data)


def change_password(username, old_pass, new_pass):
    if not verify_login(username, old_pass):
        return False
    data = _load()
    if username in data["users"]:
        data["users"][username]["password"] = _hash(new_pass)
        _save(data)
        return True
    return False


def list_users():
    data = _load()
    return list(data["users"].keys())