"""Bot buyruqlari (/ menyusi) — shaxsiy chat, guruh va admin uchun alohida.

Avval hech qanday buyruq ro'yxati o'rnatilmagan edi, shuning uchun
guruhda "/" bosilganda bot buyruqlari umuman ko'rinmasdi.
"""

import logging

from aiogram import Bot
from aiogram.types import (
    BotCommand,
    BotCommandScopeAllGroupChats,
    BotCommandScopeAllPrivateChats,
    BotCommandScopeChat,
    BotCommandScopeDefault,
)

from bot.config import ADMIN_TG_ID

log = logging.getLogger(__name__)

DEFAULT_COMMANDS = [
    BotCommand(command="start", description="Botni ishga tushirish"),
    BotCommand(command="menu", description="Asosiy menyu"),
    BotCommand(command="help", description="Yordam"),
    BotCommand(command="language", description="Tilni o'zgartirish"),
]

PRIVATE_COMMANDS = DEFAULT_COMMANDS + [
    BotCommand(command="baholarim", description="Baholarim"),
    BotCommand(command="jadvalim", description="Dars jadvalim"),
    BotCommand(command="davomatim", description="Davomatim"),
    BotCommand(command="uyvazifam", description="Uy vazifam"),
    BotCommand(command="reytingim", description="Reytingim"),
    BotCommand(command="yutuqlarim", description="Yutuqlarim"),
    BotCommand(command="farzandim", description="Farzandim (ota-ona uchun)"),
]

GROUP_COMMANDS = [
    BotCommand(command="menu", description="Botni shaxsiy chatda ochish"),
    BotCommand(command="jadval", description="Haftalik jadval"),
    BotCommand(command="reyting", description="Sinf reytingi"),
    BotCommand(command="help", description="Yordam"),
]

ADMIN_COMMANDS = PRIVATE_COMMANDS + [
    BotCommand(command="statistika", description="Sinf statistikasi"),
    BotCommand(command="oquvchilar", description="Barcha o'quvchilar"),
    BotCommand(command="sinflar", description="Sinf ma'lumoti"),
    BotCommand(command="xodimlar", description="Xodimlar ro'yxati"),
    BotCommand(command="hisobot", description="Hisobot"),
    BotCommand(command="premium", description="Premium ball jadvali"),
    BotCommand(command="elon", description="Guruhga e'lon yuborish"),
    BotCommand(command="sync", description="eMaktab bilan qo'lda sinxronlash"),
    BotCommand(command="broadcast", description="Barcha guruhlarga xabar"),
]


async def setup_commands(bot: Bot):
    """Har bir chat turi uchun mos buyruqlar ro'yxatini o'rnatadi.

    Bot guruhga tugma (reply keyboard) yubora olmaydi — Telegram
    "Group Privacy" rejimida oddiy matnlarni ko'rmaydi, faqat "/" bilan
    boshlanadigan buyruqlarni. Shuning uchun guruhda ishlash uchun
    ular albatta shu ro'yxatda bo'lishi kerak.
    """
    try:
        await bot.set_my_commands(DEFAULT_COMMANDS, scope=BotCommandScopeDefault())
        await bot.set_my_commands(PRIVATE_COMMANDS, scope=BotCommandScopeAllPrivateChats())
        await bot.set_my_commands(GROUP_COMMANDS, scope=BotCommandScopeAllGroupChats())
        if ADMIN_TG_ID:
            await bot.set_my_commands(
                ADMIN_COMMANDS, scope=BotCommandScopeChat(chat_id=ADMIN_TG_ID)
            )
        log.info("✅ Bot buyruqlari o'rnatildi (shaxsiy, guruh, admin)")
    except Exception as e:
        log.error("setup_commands xato: %s", e)
