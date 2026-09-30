"""Yordamchi funksiyalar."""

import logging
from datetime import datetime, timezone, timedelta

log = logging.getLogger(__name__)

TASHKENT_TZ = timezone(timedelta(hours=5))


# ============================================================
# VAQT
# ============================================================
def now_tashkent():
    return datetime.now(TASHKENT_TZ)


def days_uz():
    return ["Dushanba", "Seshanba", "Chorshanba",
            "Payshanba", "Juma", "Shanba", "Yakshanba"]


def today_uz() -> str:
    days = days_uz()
    return days[now_tashkent().weekday()]


def lesson_num(lesson: dict) -> int:
    """Dars raqami. eMaktab 'lessonNumber' beradi; eski 'order'/'number' ham qo'llanadi."""
    for key in ("lessonNumber", "order", "number"):
        v = lesson.get(key)
        if v:
            try:
                return int(v)
            except (TypeError, ValueError):
                pass
    return 0


# ============================================================
# TELEFON
# ============================================================
def format_phone(phone: str) -> str:
    """+998901234567 → +998 90 123 45 67"""
    if not phone:
        return "—"
    digits = "".join(c for c in phone if c.isdigit())
    if len(digits) == 12 and digits.startswith("998"):
        return (f"+{digits[:3]} {digits[3:5]} {digits[5:8]} "
                f"{digits[8:10]} {digits[10:]}")
    return phone


def normalize_phone(phone: str) -> str:
    """901234567 → +998901234567"""
    if not phone:
        return ""
    digits = "".join(c for c in phone if c.isdigit())
    if len(digits) == 9:
        digits = "998" + digits
    if not digits.startswith("998"):
        digits = "998" + digits
    return "+" + digits


# ============================================================
# BAHOLAR
# ============================================================
def score_emoji(score) -> str:
    if score is None:
        return "⚪️"
    try:
        s = float(score)
    except Exception:
        return "⚪️"
    if s >= 9:
        return "🟢"
    if s >= 7:
        return "🔵"
    if s >= 5:
        return "🟡"
    return "🔴"


def get_type_label(mark_type: str) -> str:
    t = (mark_type or "").upper()
    if "BSB" in t:
        return "BSB"
    if "CHSB" in t:
        return "CHSB"
    if "YAB" in t or "DJ" in t:
        return "Kunlik"
    return mark_type or "—"


def format_score(g: dict) -> str:
    """Baho formatlash: '9/10' yoki '38/50 (76%)'"""
    score = g.get("score")
    raw = g.get("rawValue", "")
    max_val = g.get("maxValue")
    is_percent = g.get("isPercent", False)

    if score is None:
        return raw or "—"
    if is_percent and max_val:
        return f"{raw}/{max_val} ({score}%)"
    return f"{score}/10"


# ============================================================
# XAVFSIZ OLISH
# ============================================================
def safe_get(d, *keys, default=None):
    for k in keys:
        if not isinstance(d, dict):
            return default
        d = d.get(k)
        if d is None:
            return default
    return d if d is not None else default


# ============================================================
# MATN
# ============================================================
def truncate(text: str, length: int = 100) -> str:
    if not text:
        return ""
    return text if len(text) <= length else text[:length - 3] + "..."


def escape_html(text: str) -> str:
    if not text:
        return ""
    return (text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;"))