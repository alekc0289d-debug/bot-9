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
# llama-3.3-70b-versatile Groq tomonidan 2026-08-16 da butunlay
# o'chirildi — shuning uchun AI javob bermay qolgan edi. Yangi tavsiya
# qilingan model: openai/gpt-oss-120b. Kelajakda Groq yana model
# o'zgartirsa, kodga tegmasdan GROQ_MODEL muhit o'zgaruvchisi orqali
# yangilash mumkin.
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
AI_DAILY_LIMIT = 20

# Bot versiyasi
BOT_VERSION = "1.0.0"