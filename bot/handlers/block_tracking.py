"""Foydalanuvchi botni bloklasa/blokdan chiqarsa — Firestore'da belgilash.

Avval: sayt faqat 'tgId bor-yo'qligi'ga qarab 'ulangan' deb ko'rsatardi.
Lekin odam botni bir marta ishga tushirib, keyin BLOKLASHI mumkin —
shunda tgId hujjatda saqlanib qoladi (hech qachon o'chirilmaydi), ammo
botga xabar yubora olmaymiz. Shu handler aynan shu holatni Telegram'ning
o'zidan (my_chat_member hodisasi) aniqlab, Firestore'ga yozadi — sayt
(Students.jsx) endi uni 'Bloklangan' deb alohida ko'rsatadi.
"""

import logging

from aiogram import Router
from aiogram.enums import ChatType
from aiogram.types import ChatMemberUpdated

from bot.utils.db_helpers import mark_bot_blocked

log = logging.getLogger(__name__)
router = Router()


@router.my_chat_member()
async def on_block_unblock(event: ChatMemberUpdated):
    if event.chat.type != ChatType.PRIVATE:
        return  # guruhga qo'shilish/chiqarilish — bu bot/handlers/group.py da

    status = event.new_chat_member.status
    tg_id = event.chat.id  # shaxsiy chatda chat.id == foydalanuvchi tg_id

    if status == "kicked":
        log.info("Foydalanuvchi botni bloklad: %s", tg_id)
        mark_bot_blocked(tg_id, True)
    elif status == "member":
        log.info("Foydalanuvchi botni blokdan chiqardi: %s", tg_id)
        mark_bot_blocked(tg_id, False)
