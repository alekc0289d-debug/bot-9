"""Bot konfiguratsiyasi."""

import json
import os
from pathlib import Path

from dotenv import load_dotenv

# .env ni loyiha ildizidan yuklaymiz
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR.parent / ".env")


# ============================================================
# Telegram
# ============================================================
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_TG_ID = int(os.getenv("ADMIN_TG_ID") or 0)


# ============================================================
# AI (Groq)
# ============================================================
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
AI_DAILY_LIMIT = int(os.getenv("AI_DAILY_LIMIT", "20"))


# ============================================================
# Firebase
# ------------------------------------------------------------
# .env da FIREBASE_CREDENTIALS_JSON (to'liq JSON matni, bir qatorli)
# bo'lishi kerak. Ixtiyoriy: FIREBASE_DB_URL.
# ============================================================
FIREBASE_CREDENTIALS_JSON = os.getenv("FIREBASE_CREDENTIALS_JSON", "").strip()
FIREBASE_DB_URL = os.getenv("FIREBASE_DB_URL", "")


def get_firebase_credentials() -> dict:
    """Firebase service account ma'lumotlarini dict ko'rinishida qaytaradi.

    Avval FIREBASE_CREDENTIALS_JSON (env) dan o'qiydi. Agar u bo'sh bo'lsa,
    loyiha ildizidagi firebase_key.json faylidan o'qishga urinadi (fallback).
    """
    raw = FIREBASE_CREDENTIALS_JSON

    if not raw:
        # Fallback: fayl orqali
        path = BASE_DIR.parent / "firebase_key.json"
        if path.is_file():
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        raise ValueError(
            "FIREBASE_CREDENTIALS_JSON env topilmadi va firebase_key.json "
            "fayli ham mavjud emas."
        )

    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"FIREBASE_CREDENTIALS_JSON noto'g'ri JSON: {e}")


# ============================================================
# Tillar
# ============================================================
LANGUAGES = {
    "uz": "🇺🇿 O'zbekcha",
    "uz-cyrl": "🇺🇿 Ўзбекча",
    "ru": "🇷🇺 Русский",
}
DEFAULT_LANG = "uz"


# ============================================================
# Maktab
# ============================================================
SCHOOL_NAME = os.getenv("SCHOOL_NAME", "Maktab")
CLASS_NAME = os.getenv("CLASS_ID", "9-A")


# ============================================================
# Bot versiyasi
# ============================================================
BOT_VERSION = "1.0.0"


# ============================================================
# settings obyekti
# ------------------------------------------------------------
# Quyidagi wrapper orqali:
#   settings.BOT_TOKEN
#   settings.FIREBASE_CREDENTIALS_JSON
#   settings.firebase_credentials_json   (kichik harf ham ishlaydi)
# kabi murojaatlar ishlaydi. Agar modul o'zgaruvchisida topilmasa,
# to'g'ridan-to'g'ri os.environ dan ham qidiradi.
# ============================================================
class _Settings:
    def __getattr__(self, name: str):
        # 1) modul o'zgaruvchisi (aynan nom bilan)
        if name in globals():
            return globals()[name]

        # 2) katta harfli variant
        upper = name.upper()
        if upper in globals():
            return globals()[upper]

        # 3) env dan (katta harf bilan)
        val = os.getenv(upper)
        if val is not None:
            return val

        # 4) env dan (aynan shu nom bilan)
        val = os.getenv(name)
        if val is not None:
            return val

        raise AttributeError(f"config has no setting: {name}")


settings = _Settings()