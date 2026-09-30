"""Handler: /start, til tanlash, telefon raqam, rol aniqlash."""

import asyncio
import logging
from datetime import datetime, timezone

from aiogram import Router, F
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import Message, CallbackQuery

from bot.config import CLASS_NAME
from bot.keyboards import reply, inline
from bot.locales.loader import t, set_user_lang
from bot.utils.db_helpers import resolve_user, save_user_lang
from bot.utils.helpers import normalize_phone, format_phone
from firebase_client import db

log = logging.getLogger(__name__)
router = Router()


# ============================================================
# /start
# ============================================================
@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject):
    tg_id = message.from_user.id
    name = message.from_user.full_name

    log.info("/start: %s (%s) | args=%s",
             name, tg_id, command.args)

    # Agar foydalanuvchi allaqachon ro'yxatdan o'tgan bo'lsa
    existing = await asyncio.to_thread(find_user_by_tg, tg_id)
    if existing:
        await show_role_menu(message, existing)
        return

    # Yangi — til tanlash
    await message.answer(
        "🎓 <b>Assalomu alaykum!</b>\n\n"
        "Maktab Boshqaruv Botiga xush kelibsiz.\n\n"
        "🌐 Iltimos, tilni tanlang:",
    )
    await message.answer(
        "🌐 <b>Tilni tanlang</b> / <b>Выберите язык</b>",
        reply_markup=inline.language_keyboard(),
    )


# ============================================================
# TIL TANLANGANDA
# ============================================================
@router.callback_query(F.data.startswith("lang:"))
async def handle_lang(callback: CallbackQuery):
    lang = callback.data.split(":")[1]
    tg_id = callback.from_user.id

    set_user_lang(tg_id, lang)
    await asyncio.to_thread(save_user_lang, tg_id, lang)
    log.info("Til tanlandi: %s → %s", tg_id, lang)

    await callback.message.edit_text(
        t("lang_selected", tg_id=tg_id)
    )

    # Telefon raqam so'rash
    await callback.message.answer(
        t("share_phone_prompt", tg_id=tg_id),
        reply_markup=reply.phone_keyboard(tg_id),
    )
    await callback.answer()


# ============================================================
# TELEFON RAQAM OLINGANDA
# ============================================================
@router.message(F.contact)
async def handle_contact(message: Message):
    tg_id = message.from_user.id
    phone = message.contact.phone_number

    if message.contact.user_id != tg_id:
        await message.answer(t("share_own_phone", tg_id=tg_id))
        return

    normalized = normalize_phone(phone)
    log.info("Telefon olindi: %s → %s", tg_id, normalized)

    await message.answer(
        t("phone_received", tg_id=tg_id, phone=format_phone(normalized))
    )

    # Foydalanuvchini topish
    user = await asyncio.to_thread(find_user_by_phone, normalized)

    if not user:
        await message.answer(
            t("user_not_found", tg_id=tg_id)
        )
        return

    # Telefonni saqlash
    await asyncio.to_thread(
        save_user_tg, user["id"], tg_id, normalized,
        user.get("role", "student"), user.get("_coll"),
    )

    # Rol bo'yicha menyu
    await show_role_menu(message, user, normalized)


# ============================================================
# ROL BO'YICHA MENYU
# ============================================================
async def show_role_menu(message_or_user, user: dict, phone: str = None):
    """Rolga qarab menyu ko'rsatish."""
    from_user = getattr(message_or_user, "from_user", None)
    tg_id = from_user.id if from_user else user.get("tgId")
    role = user.get("role", "student")
    name = user.get("fullName") or user.get("name") or "Foydalanuvchi"
    class_name = user.get("classId") or CLASS_NAME

    role_key = {
        "student": "role_student",
        "parent": "role_parent",
        "teacher": "role_teacher",
        "admin": "role_admin",
    }.get(role, "role_student")

    text = (
        f"{t(role_key, tg_id=tg_id)}\n\n"
        + t("welcome_user", tg_id=tg_id, name=name, class_name=class_name)
        + "\n\n"
        + t("menu_title", tg_id=tg_id)
    )

    menu = reply.get_menu_by_role(role, tg_id)

    await message_or_user.answer(text, reply_markup=menu)


# ============================================================
# FIRESTORE — FOYDALANUVCHI QIDIRISH
# ============================================================
def find_user_by_tg(tg_id: int):
    """Telegram ID bo'yicha foydalanuvchi (rol bilan) — bitta joyda hal qilinadi."""
    return resolve_user(tg_id)


def find_user_by_phone(phone: str):
    """Telefon raqam bo'yicha foydalanuvchi topish."""
    try:
        client = db()

        # students: phone, motherPhone, fatherPhone
        for field in ("phone", "motherPhone", "fatherPhone"):
            snap = list(
                client.collection("students")
                .where(field, "==", phone)
                .limit(1)
                .stream()
            )
            if snap:
                data = snap[0].to_dict()
                data["id"] = snap[0].id
                data["_coll"] = "students"
                data["role"] = (
                    "student" if field == "phone" else "parent"
                )
                return data

        # staff
        snap = list(
            client.collection("staff")
            .where("phone", "==", phone)
            .limit(1)
            .stream()
        )
        if snap:
            data = snap[0].to_dict()
            data["id"] = snap[0].id
            data["_coll"] = "staff"
            if "role" not in data:
                data["role"] = "teacher"
            return data

    except Exception as e:
        log.error("find_user_by_phone xato: %s", e)
    return None


def save_user_tg(user_id: str, tg_id: int, phone: str,
                 role: str = "student", coll: str | None = None):
    """
    Telegram ID ni saqlash.

    - o'quvchi / o'qituvchi: tgId va phone yoziladi
    - ota-ona: parentTgId yoziladi (o'quvchining tgId va telefoni
      ustidan YOZILMAYDI)
    """
    try:
        client = db()
        now = datetime.now(timezone.utc)
        colls = (coll,) if coll else ("students", "staff", "users")

        for c in colls:
            ref = client.collection(c).document(user_id)
            if not ref.get().exists:
                continue
            if role == "parent":
                data = {"parentTgId": tg_id, "parentRegisteredAt": now}
            else:
                data = {"tgId": tg_id, "phone": phone, "registeredAt": now}
            ref.set(data, merge=True)
            log.info("%s/%s (%s) Telegram ID saqlandi", c, user_id, role)
            return
        log.warning("save_user_tg: %s topilmadi", user_id)
    except Exception as e:
        log.error("save_user_tg xato: %s", e)
