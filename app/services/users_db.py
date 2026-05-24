"""Simple JSON-based user database."""
import json
import os
import time
from pathlib import Path
from typing import Optional

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
USERS_FILE = DATA_DIR / "users.json"
WAITLIST_FILE = DATA_DIR / "waitlist.json"


def _ensure_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load(path: Path) -> dict:
    _ensure_dir()
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(path: Path, data: dict):
    _ensure_dir()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ---- Users ----

def save_user(user_id: int, username: str = "", first_name: str = "", last_name: str = ""):
    """Save or update user info."""
    users = _load(USERS_FILE)
    uid = str(user_id)
    now = int(time.time())
    if uid in users:
        users[uid]["username"] = username
        users[uid]["first_name"] = first_name
        users[uid]["last_name"] = last_name
        users[uid]["last_seen"] = now
    else:
        users[uid] = {
            "user_id": user_id,
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "first_seen": now,
            "last_seen": now,
        }
    _save(USERS_FILE, users)


def get_all_users() -> list[dict]:
    """Return list of all users."""
    return list(_load(USERS_FILE).values())


def get_user(user_id: int) -> Optional[dict]:
    users = _load(USERS_FILE)
    return users.get(str(user_id))


def get_user_count() -> int:
    return len(_load(USERS_FILE))


# ---- Waiting list ----

def get_waitlist() -> list[int]:
    """Return list of user IDs in waitlist."""
    data = _load(WAITLIST_FILE)
    return data.get("ids", [])


def set_waitlist(ids: list[int]):
    """Replace entire waitlist."""
    _save(WAITLIST_FILE, {"ids": ids})


def add_to_waitlist(user_id: int):
    wl = get_waitlist()
    if user_id not in wl:
        wl.append(user_id)
        set_waitlist(wl)


def remove_from_waitlist(user_id: int):
    wl = get_waitlist()
    if user_id in wl:
        wl.remove(user_id)
        set_waitlist(wl)


def clear_waitlist():
    set_waitlist([])
