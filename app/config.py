import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Settings:
    bot_token: str
    candidates_group_id: int

def get_settings() -> Settings:
    token = os.getenv("BOT_TOKEN", "").strip()
    group_id_str = os.getenv("CANDIDATES_GROUP_ID", "0").strip() or "0"

    try:
        group_id = int(group_id_str)
    except ValueError:
        group_id = 0

    if not token:
        raise RuntimeError("BOT_TOKEN is missing (env)")

    return Settings(
        bot_token=token,
        candidates_group_id=group_id,
    )
