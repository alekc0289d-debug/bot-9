"""Reply keyboardlar — barcha rollar uchun."""

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from bot.locales.loader import t


def language_keyboard():
    """Til tanlash (oddiy, inline ishlatamiz odatda)."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🇺🇿 O'zbekcha")],
            [KeyboardButton(text="🇺🇿 Ўзбекча")],
            [KeyboardButton(text="🇷🇺 Русский")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def phone_keyboard(tg_id: int):
    """Telefon raqam so'rash."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(
                text=t("share_phone_button", tg_id=tg_id),
                request_contact=True,
            )],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def student_menu(tg_id: int):
    """O'quvchi asosiy menyusi."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=t("btn_grades", tg_id=tg_id)),
                KeyboardButton(text=t("btn_schedule", tg_id=tg_id)),
            ],
            [
                KeyboardButton(text=t("btn_attendance", tg_id=tg_id)),
                KeyboardButton(text=t("btn_homework", tg_id=tg_id)),
            ],
            [
                KeyboardButton(text=t("btn_rating", tg_id=tg_id)),
                KeyboardButton(text=t("btn_achievements", tg_id=tg_id)),
            ],
            [
                KeyboardButton(text=t("btn_daily_grades", tg_id=tg_id)),
                KeyboardButton(text=t("btn_ai", tg_id=tg_id)),
            ],
            [
                KeyboardButton(text=t("btn_settings", tg_id=tg_id)),
            ],
        ],
        resize_keyboard=True,
    )


def parent_menu(tg_id: int):
    """Ota-ona asosiy menyusi."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=t("btn_child", tg_id=tg_id)),
                KeyboardButton(text=t("btn_parent_grades", tg_id=tg_id)),
            ],
            [
                KeyboardButton(text=t("btn_parent_attendance", tg_id=tg_id)),
                KeyboardButton(text=t("btn_parent_schedule", tg_id=tg_id)),
            ],
            [
                KeyboardButton(text=t("btn_homework", tg_id=tg_id)),
                KeyboardButton(text=t("btn_parent_rating", tg_id=tg_id)),
            ],
            [
                KeyboardButton(text=t("btn_payments", tg_id=tg_id)),
                KeyboardButton(text=t("btn_contact", tg_id=tg_id)),
            ],
            [
                KeyboardButton(text=t("btn_ai", tg_id=tg_id)),
                KeyboardButton(text=t("btn_settings", tg_id=tg_id)),
            ],
        ],
        resize_keyboard=True,
    )


def teacher_menu(tg_id: int):
    """O'qituvchi asosiy menyusi."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=t("btn_classes", tg_id=tg_id)),
                KeyboardButton(text=t("btn_students", tg_id=tg_id)),
            ],
            [
                KeyboardButton(text=t("btn_mark_attendance", tg_id=tg_id)),
                KeyboardButton(text=t("btn_mark_grade", tg_id=tg_id)),
            ],
            [
                KeyboardButton(text=t("btn_teacher_homework", tg_id=tg_id)),
                KeyboardButton(text=t("btn_teacher_schedule", tg_id=tg_id)),
            ],
            [
                KeyboardButton(text=t("btn_announce", tg_id=tg_id)),
                KeyboardButton(text=t("btn_stats", tg_id=tg_id)),
            ],
            [
                KeyboardButton(text=t("btn_ai", tg_id=tg_id)),
                KeyboardButton(text=t("btn_settings", tg_id=tg_id)),
            ],
        ],
        resize_keyboard=True,
    )


def admin_menu(tg_id: int):
    """Admin asosiy menyusi."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=t("btn_stats", tg_id=tg_id)),
                KeyboardButton(text=t("btn_admin_students", tg_id=tg_id)),
            ],
            [
                KeyboardButton(text=t("btn_admin_classes", tg_id=tg_id)),
                KeyboardButton(text=t("btn_admin_staff", tg_id=tg_id)),
            ],
            [
                KeyboardButton(text=t("btn_admin_grades", tg_id=tg_id)),
                KeyboardButton(text=t("btn_admin_schedule", tg_id=tg_id)),
            ],
            [
                KeyboardButton(text=t("btn_announce", tg_id=tg_id)),
                KeyboardButton(text=t("btn_admin_rating", tg_id=tg_id)),
            ],
            [
                KeyboardButton(text=t("btn_premium", tg_id=tg_id)),
                KeyboardButton(text=t("btn_report", tg_id=tg_id)),
            ],
            [
                KeyboardButton(text=t("btn_sync", tg_id=tg_id)),
                KeyboardButton(text=t("btn_settings", tg_id=tg_id)),
            ],
            [
                KeyboardButton(text=t("btn_broadcast", tg_id=tg_id)),
            ],
        ],
        resize_keyboard=True,
    )


def get_menu_by_role(role: str, tg_id: int):
    """Rolga qarab menyu qaytarish."""
    menus = {
        "student": student_menu,
        "parent": parent_menu,
        "teacher": teacher_menu,
        "admin": admin_menu,
    }
    fn = menus.get(role, student_menu)
    return fn(tg_id)