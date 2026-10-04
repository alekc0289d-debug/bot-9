"""Foydalanuvchi tilini Firestore'dan bir marta yuklash (qayta ishga tushgandan keyin ham).

Bu middleware HAR BIR xabarda (kamida bir marta, foydalanuvchi uchun)
ishlaydi, shuning uchun Firestore sekinlashganda BUTUN bot shu yerda
qotib qolmasligi uchun qisqa vaqt chegarasi bilan ishlaydi — timeout
bo'lsa ham xabarni qayta ishlashni to'xtatmaydi (keyingi urinishda
qayta sinab ko'radi).
"""

import asyncio
import logging

from aiogram import BaseMiddleware

from bot.locales.loader import is_lang_checked, mark_lang_checked
from bot.utils.db_helpers import resolve_user

log = logging.getLogger(__name__)

_TIMEOUT = 6  # soniya


class LangMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user = data.get("event_from_user")
        if user and not is_lang_checked(user.id):
            try:
                # resolve_user topilgan tilni o'zi o'rnatadi
                await asyncio.wait_for(
                    asyncio.to_thread(resolve_user, user.id), timeout=_TIMEOUT
                )
                mark_lang_checked(user.id)
            except asyncio.TimeoutError:
                log.warning(
                    "LangMiddleware: resolve_user %s soniyada javob bermadi (tg_id=%s)",
                    _TIMEOUT, user.id,
                )
                # mark_lang_checked QILMAYMIZ — keyingi xabarda qayta sinaydi
        return await handler(event, data)
