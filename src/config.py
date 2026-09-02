import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "8728398396:AAFP3oouTqX5__Q3ws7LoKwJEbfoNJ4q6PY")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

ADMIN_IDS = []
_raw_admins = os.getenv("ADMIN_IDS", "")
if _raw_admins:
    for p in _raw_admins.split(","):
        p = p.strip()
        if p.isdigit():
            ADMIN_IDS.append(int(p))

DB_PATH = os.getenv("DB_PATH", "bot.db")
RETENTION_DAYS = int(os.getenv("RETENTION_DAYS", "90"))
RATE_LIMIT_COUNT = int(os.getenv("RATE_LIMIT_COUNT", "5"))
RATE_LIMIT_SECONDS = int(os.getenv("RATE_LIMIT_SECONDS", "10"))
