"""Bot konfiguratsiyasi."""

import base64
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

# llama-3.3-70b-versatile Groq tomonidan 2026-08-16 da butunlay
# o'chirildi. Yangi tavsiya qilingan model: openai/gpt-oss-120b.
# Kelajakda modelni kodga tegmasdan GROQ_MODEL env orqali o'zgartirish mumkin.
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
AI_DAILY_LIMIT = int(os.getenv("AI_DAILY_LIMIT", "20"))


# ============================================================
# Firebase
# ------------------------------------------------------------
# Endi credentials env orqali beriladi. Ikki xil usul qo'llab-quvvatlanadi:
#
#   1) FIREBASE_CREDENTIALS_JSON — service account JSON ning TO'LIQ matni
#      (bir qatorli yoki ko'p qatorli string).
#
#   2) FIREBASE_CREDENTIALS_B64  — o'sha JSON ning base64 ko'rinishi
#      (Docker/Railway/Render kabi platformalarda ko'p qatorli string
#       muammo bo'lganda qulay).
#
# Agar ikkalasi ham bo'sh bo'lsa, FIREBASE_CREDENTIALS_FILE orqali
# fayl yo'lini ko'rsatish ham mumkin (fallback).
# ============================================================
FIREBASE_CREDENTIALS_JSON = os.getenv("FIREBASE_CREDENTIALS_JSON", "").strip()
FIREBASE_CREDENTIALS_B64 = os.getenv("FIREBASE_CREDENTIALS_B64", "").strip()
FIREBASE_CREDENTIALS_FILE = os.getenv(
    "FIREBASE_CREDENTIALS_FILE",
    str(BASE_DIR.parent / "firebase_key.json"),
)

FIREBASE_DB_URL = os.getenv("FIREBASE_DB_URL", "")


def get_firebase_credentials() -> dict:
    """Firebase service account ma'lumotlarini dict ko'rinishida qaytaradi.

    Ustuvorlik:
      1) FIREBASE_CREDENTIALS_B64  (base64 -> JSON)
      2) FIREBASE_CREDENTIALS_JSON (to'g'ridan-to'g'ri JSON matni)
      3) FIREBASE_CREDENTIALS_FILE (fayldan o'qish)

    Topilmasa — FileNotFoundError / ValueError ko'taradi.
    """
    # 1) base64
    if FIREBASE_CREDENTIALS_B64:
        try:
            decoded = base64.b64decode(FIREBASE_CREDENTIALS_B64).decode("utf-8")
            return json.loads(decoded)
        except Exception as e:
            raise ValueError(
                f"FIREBASE_CREDENTIALS_B64 ni decode qilib bo'lmadi: {e}"
            )

    # 2) to'g'ridan-to'g'ri JSON matni
    if FIREBASE_CREDENTIALS_JSON:
        try:
            return json.loads(FIREBASE_CREDENTIALS_JSON)
        except Exception as e:
            raise ValueError(
                f"FIREBASE_CREDENTIALS_JSON noto'g'ri JSON: {e}"
            )

    # 3) fayldan o'qish (fallback)
    path = Path(FIREBASE_CREDENTIALS_FILE)
    if path.is_file():
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    raise FileNotFoundError(
        "Firebase credentials topilmadi. .env da FIREBASE_CREDENTIALS_B64 "
        "yoki FIREBASE_CREDENTIALS_JSON ni o'rnating, yoki "
        f"FIREBASE_CREDENTIALS_FILE yo'lini to'g'rilang ({path})."
    )


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
# firebase_client.py va boshqa fayllar `from config import settings`
# ishlatadi. Quyidagi wrapper yuqoridagi modul o'zgaruvchilariga
# settings.XXX ko'rinishida murojaat qilish imkonini beradi:
#   settings.BOT_TOKEN, settings.FIREBASE_DB_URL, ...
# ============================================================
class _Settings:
    def __getattr__(self, name: str):
        try:
            return globals()[name]
        except KeyError:
            raise AttributeError(f"config has no setting: {name}")


settings = _Settings()