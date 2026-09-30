"""Guruh boshqaruvi — bot guruhga qo'shilganda avtomatik tanishtirish."""

import logging
from datetime import datetime, timezone

from aiogram import Router
from aiogram.filters import ChatMemberUpdatedFilter, IS_NOT_MEMBER, IS_MEMBER
from aiogram.types import ChatMemberUpdated

from bot.keyboards import inline
from firebase_client import db

log = logging.getLogger(__name__)
router = Router()

INTRO_TEXT = """🎓 <b>Assalomu alaykum, hurmatli o'qituvchilar, o'quvchilar va ota-onalar!</b>

Men — <b>Maktab Boshqaruv Boti</b> 🤖
Sizga maktab hayotini osonlashtirish uchun yaratilganman.

━━━━━━━━━━━━━━━━━━━━━━
<b>📚 MEN NIMA QILA OLAMAN?</b>
━━━━━━━━━━━━━━━━━━━━━━

📊 Baholaringizni ko'rish
📅 Dars jadvali
📔 Davomat
📚 Uy vazifalari
🏆 Sinf reytingi
🤖 AI o'qituvchi

━━━━━━━━━━━━━━━━━━━━━━
<b>🎁 MOTIVATSIYA</b>
━━━━━━━━━━━━━━━━━━━━━━

🏆 Har oy eng yaxshi o'quvchi <b>Telegram Premium</b> bilan taqdirlanadi!

━━━━━━━━━━━━━━━━━━━━━━
Pastdagi <b>«Ishga tushirish»</b> tugmasini bosing 👇
"""


@router.my_chat_member(
    ChatMemberUpdatedFilter(IS_NOT_MEMBER >> IS_MEMBER)
)
async def bot_added(event: ChatMemberUpdated):
    """Bot guruhga qo'shildi."""
    from bot.instance import bot

    chat = event.chat
    added_by = event.from_user

    log.info("Bot qo'shildi: %s (%s) | %s",
             chat.title, chat.id, added_by.full_name)

    # Firestore'ga saqlash
    try:
        client = db()
        client.collection("bot_groups").document(str(chat.id)).set({
            "chatId": chat.id,
            "title": chat.title,
            "type": chat.type,
            "addedBy": added_by.id,
            "addedByName": added_by.full_name,
            "addedAt": datetime.now(timezone.utc),
            "active": True,
        }, merge=True)
    except Exception as e:
        log.error("Guruh saqlash xato: %s", e)

    # Avtomatik tanishtirish
    try:
        me = await bot.get_me()
        kb = inline.intro_start_button(me.username)
        await bot.send_message(
            chat_id=chat.id,
            text=INTRO_TEXT,
            reply_markup=kb,
            disable_web_page_preview=True,
        )
    except Exception as e:
        log.error("Tanishtirish xato: %s", e)


@router.my_chat_member(
    ChatMemberUpdatedFilter(IS_MEMBER >> IS_NOT_MEMBER)
)
async def bot_removed(event: ChatMemberUpdated):
    """Bot guruhdan chiqarildi."""
    chat = event.chat
    log.info("Bot chiqarildi: %s (%s)", chat.title, chat.id)

    try:
        client = db()
        client.collection("bot_groups").document(str(chat.id)).set({
            "active": False,
        }, merge=True)
    except Exception as e:
        log.error("Yangilash xato: %s", e)