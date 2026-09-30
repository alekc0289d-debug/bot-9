"""Foydalanuvchi tilini Firestore'dan bir marta yuklash (qayta ishga tushgandan keyin ham)."""

import asyncio

from aiogram import BaseMiddleware

from bot.locales.loader import is_lang_checked, mark_lang_checked
from bot.utils.db_helpers import resolve_user


class LangMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user = data.get("event_from_user")
        if user and not is_lang_checked(user.id):
            # resolve_user topilgan tilni o'zi o'rnatadi
            await asyncio.to_thread(resolve_user, user.id)
            mark_lang_checked(user.id)
        return await handler(event, data)
