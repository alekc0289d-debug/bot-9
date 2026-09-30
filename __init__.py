"""Bot konfiguratsiyasi."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_TG_ID = int(os.getenv("ADMIN_TG_ID") or 0)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# Tillar
LANGUAGES = {
    "uz": "🇺🇿 O'zbekcha",
    "uz-cyrl": "🇺🇿 Ўзбекча",
    "ru": "🇷🇺 Русский",
}
DEFAULT_LANG = "uz"

# Maktab
SCHOOL_NAME = "Maktab"
CLASS_NAME = os.getenv("CLASS_ID", "9-A")

# AI
GROQ_MODEL = "llama-3.3-70b-versatile"
AI_DAILY_LIMIT = 20

# Bot versiyasi
BOT_VERSION = "1.0.0"