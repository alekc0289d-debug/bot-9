"""Asosiy menyu — barcha rol tugmalarini marshrutlash."""

import logging

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from aiogram.enums import ChatType

from bot.keyboards import reply, inline
from bot.locales.loader import t, get_user_lang
from bot.utils.db_helpers import resolve_user, get_schedule, get_rating, get_settings
from bot.utils.helpers import format_phone, lesson_num, days_uz, today_uz

from firebase_client import db

log = logging.getLogger(__name__)
router = Router()


# ============================================================
# YORDAMCHI: foydalanuvchini aniqlash
# ============================================================
def _resolve_user(tg_id: int) -> dict | None:
    """tgId bo'yicha foydalanuvchi va roli (student/parent/teacher/admin)."""
    return resolve_user(tg_id)


# ============================================================
# /menu va "Sozlamalar" / orqaga
# ============================================================
@router.message(Command("menu"))
async def cmd_menu(message: Message):
    user = _resolve_user(message.from_user.id)
    if not user:
        await message.answer(t("user_not_found", tg_id=message.from_user.id))
        return
    role = user.get("role", "student")
    name = user.get("fullName") or user.get("name") or "Foydalanuvchi"
    class_name = user.get("classId", "9-A")

    role_key = {
        "student": "role_student",
        "parent": "role_parent",
        "teacher": "role_teacher",
        "admin": "role_admin",
    }.get(role, "role_student")

    text = (
        f"{t(role_key, tg_id=message.from_user.id)}\n\n"
        + t("welcome_user", tg_id=message.from_user.id,
            name=name, class_name=class_name)
        + "\n\n"
        + t("menu_title", tg_id=message.from_user.id)
    )

    await message.answer(text, reply_markup=reply.get_menu_by_role(role, message.from_user.id))


@router.message(Command("help"))
async def cmd_help(message: Message):
    tg_id = message.from_user.id
    if message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await message.answer(t("help_group", tg_id=tg_id))
        return
    await message.answer(
        "ℹ️ <b>Yordam</b>\n\n"
        "Quyidagi buyruqlar mavjud:\n"
        "• /start — boshlash\n"
        "• /menu — asosiy menyu\n"
        "• /help — yordam\n"
        "• /settings — sozlamalar\n"
        "• /language — tilni o'zgartirish\n\n"
        "Menyu tugmalaridan ham foydalanishingiz mumkin.",
    )


# ============================================================
# GURUHDA ISHLAYDIGAN BUYRUQLAR (rolga bog'liq emas — sinf umumiy)
# ============================================================
@router.message(Command("jadval"))
async def cmd_group_schedule(message: Message):
    s = get_settings()
    class_id = s.get("className", "9-A")
    lessons = get_schedule(class_id)
    if not lessons:
        await message.answer(f"📅 {class_id} jadvali hozircha yuklanmagan.")
        return

    by_day: dict = {}
    for l in lessons:
        day = l.get("dayOfWeek") or l.get("day") or "—"
        by_day.setdefault(day, []).append(l)

    today = today_uz()
    text = f"📅 <b>{class_id} — Haftalik jadval</b>\n\n"
    for day in days_uz():
        if day not in by_day:
            continue
        mark = " 🔸" if day == today else ""
        text += f"<b>{day}{mark}</b>\n"
        for l in sorted(by_day[day], key=lesson_num):
            text += f"  {lesson_num(l) or '—'}. {l.get('subject')}\n"
        text += "\n"

    await message.answer(text)


@router.message(Command("reyting"))
async def cmd_group_rating(message: Message):
    s = get_settings()
    rating = get_rating(s.get("className", "9-A"))
    if not rating:
        await message.answer("🏆 Reyting hozircha mavjud emas.")
        return

    medals = ["🥇", "🥈", "🥉"]
    text = "🏆 <b>Sinf reytingi</b>\n\n"
    for i, r in enumerate(rating[:10]):
        prefix = medals[i] if i < 3 else f"{i+1}."
        text += f"{prefix} {r['fullName']} — <b>{r['avg']}</b>\n"

    await message.answer(text)


@router.message(Command("language"))
async def cmd_language(message: Message):
    await message.answer(
        "🌐 <b>Tilni tanlang</b> / <b>Выберите язык</b>",
        reply_markup=inline.language_keyboard(),
    )


# ============================================================
# SOZLAMALAR tugmasi
# ============================================================
@router.message(F.text.in_({
    "⚙️ Sozlamalar", "⚙ Sozlamalar", "Sozlamalar",
    "⚙️ Настройки", "Настройки",
    "⚙️ Созламалар", "Созламалар",
}))
async def handle_settings(message: Message):
    tg_id = message.from_user.id
    lang = get_user_lang(tg_id)
    user = _resolve_user(tg_id)
    role = (user or {}).get("role", "student")

    text = (
        "⚙️ <b>Sozlamalar</b>\n\n"
        f"🌐 Til: <b>{lang}</b>\n"
        f"👤 Rol: <b>{role}</b>\n"
    )
    if user:
        text += f"📛 Ism: <b>{user.get('fullName', '—')}</b>\n"
        if user.get("classId"):
            text += f"🏫 Sinf: <b>{user['classId']}</b>\n"
        if user.get("phone"):
            text += f"📞 Telefon: <b>{format_phone(user['phone'])}</b>\n"

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌐 Tilni o'zgartirish", callback_data="settings:lang")],
        [InlineKeyboardButton(text="🔄 Menyu yangilash", callback_data="settings:menu")],
    ])

    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data == "settings:lang")
async def settings_lang(callback):
    await callback.message.answer(
        "🌐 <b>Tilni tanlang</b>",
        reply_markup=inline.language_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "settings:menu")
async def settings_menu(callback):
    user = _resolve_user(callback.from_user.id)
    role = (user or {}).get("role", "student")
    await callback.message.answer(
        "✅ Menyu yangilandi",
        reply_markup=reply.get_menu_by_role(role, callback.from_user.id),
    )
    await callback.answer()


# ============================================================
# AI tugmasi
# ============================================================
@router.message(F.text.in_({
    "🤖 AI", "🤖 AI yordamchi", "AI", "🤖 ИИ", "ИИ", "🤖 АИ",
}))
async def handle_ai_button(message: Message, state: FSMContext):
    from bot.handlers.ai import start_ai_chat
    await start_ai_chat(message, state)