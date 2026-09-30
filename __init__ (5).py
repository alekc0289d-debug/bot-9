"""Til fayllarini yuklash va tarjima qilish."""

import json
import logging
from pathlib import Path
from typing import Dict

log = logging.getLogger(__name__)

LOCALES_DIR = Path(__file__).parent
_translations: Dict[str, dict] = {}
_user_langs: Dict[int, str] = {}  # {tg_id: lang}
_checked: set = set()  # Firestore'dan tili tekshirilgan foydalanuvchilar


def is_lang_checked(tg_id: int) -> bool:
    return tg_id in _checked


def mark_lang_checked(tg_id: int):
    _checked.add(tg_id)


def load_all():
    """Barcha til fayllarini yuklash."""
    for lang in ("uz", "uz-cyrl", "ru"):
        try:
            path = LOCALES_DIR / f"{lang}.json"
            with open(path, encoding="utf-8") as f:
                _translations[lang] = json.load(f)
            log.info("Til yuklandi: %s (%s kalit)",
                     lang, len(_translations[lang]))
        except Exception as e:
            log.error("Til yuklash xato %s: %s", lang, e)
            _translations[lang] = {}


def set_user_lang(tg_id: int, lang: str):
    """Foydalanuvchi tilini eslab qolish."""
    if lang in _translations:
        _user_langs[tg_id] = lang
        _checked.add(tg_id)


def get_user_lang(tg_id: int) -> str:
    """Foydalanuvchi tilini olish."""
    return _user_langs.get(tg_id, "uz")


def t(key: str, tg_id: int = None, lang: str = None, **kwargs) -> str:
    """
    Tarjima olish.
    t("welcome", tg_id=123)
    t("avg_grade", lang="ru", avg=8.5)
    """
    if lang is None and tg_id is not None:
        lang = get_user_lang(tg_id)
    if lang is None:
        lang = "uz"

    text = _translations.get(lang, {}).get(key)
    if text is None:
        text = _translations.get("uz", {}).get(key, f"[{key}]")

    if kwargs:
        try:
            text = text.format(**kwargs)
        except Exception:
            pass

    return text


# Boshlang'ich yuklash
load_all()