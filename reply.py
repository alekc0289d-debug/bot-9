"""Inline keyboards — kontekstli tugmalar."""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from bot.locales.loader import t


def language_keyboard():
    """Til tanlash — 3 til."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="🇺🇿 O'zbekcha (lotin)",
                callback_data="lang:uz",
            )],
            [InlineKeyboardButton(
                text="🇺🇿 Ўзбекча (кирилл)",
                callback_data="lang:uz-cyrl",
            )],
            [InlineKeyboardButton(
                text="🇷🇺 Русский",
                callback_data="lang:ru",
            )],
        ]
    )


def main_menu(tg_id: int):
    """Asosiy menyu — inline (ixtiyoriy)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=t("btn_grades", tg_id=tg_id),
                callback_data="grades:view",
            )],
            [InlineKeyboardButton(
                text=t("btn_schedule", tg_id=tg_id),
                callback_data="schedule:view",
            )],
            [InlineKeyboardButton(
                text=t("btn_rating", tg_id=tg_id),
                callback_data="rating:view",
            )],
            [InlineKeyboardButton(
                text=t("btn_ai", tg_id=tg_id),
                callback_data="ai:start",
            )],
        ]
    )


def grades_keyboard(tg_id: int):
    """Baholar uchun amallar."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📈 Grafik",
                    callback_data="grades:chart",
                ),
                InlineKeyboardButton(
                    text="📅 Tarix",
                    callback_data="grades:history",
                ),
            ],
            [InlineKeyboardButton(
                text="📥 PDF",
                callback_data="grades:pdf",
            )],
        ]
    )


def schedule_keyboard(tg_id: int):
    """Jadval uchun amallar."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📅 Haftalik",
                    callback_data="schedule:week",
                ),
                InlineKeyboardButton(
                    text="🗓 Ertaga",
                    callback_data="schedule:tomorrow",
                ),
            ],
        ]
    )


def admin_broadcast_confirm():
    """Botni tanishtirish tasdiqlash."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="✅ Ha, yuborish",
                callback_data="intro:send",
            )],
            [InlineKeyboardButton(
                text="❌ Bekor qilish",
                callback_data="intro:cancel",
            )],
        ]
    )


def intro_start_button(bot_username: str):
    """Botni tanishtirish uchun 'Ishga tushirish'."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="🚀 Ishga tushirish",
                url=f"https://t.me/{bot_username}?start=true",
            )],
        ]
    )


def premium_actions(student_id: str):
    """Premium g'olib uchun amallar."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="✅ Premium berdim",
                callback_data=f"premium:given:{student_id}",
            )],
            [InlineKeyboardButton(
                text="⏭ O'tkazib yuborish",
                callback_data=f"premium:skip:{student_id}",
            )],
            [InlineKeyboardButton(
                text="📊 To'liq reyting",
                callback_data="rating:full",
            )],
        ]
    )