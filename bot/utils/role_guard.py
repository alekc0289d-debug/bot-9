"""Tugma/buyruq matni bir necha rolda bir xil bo'lib qolsa ham,
faqat HAQIQIY rolga mos handler ishga tushishini ta'minlaydi.

Avval: har bir rol handleri faqat matnga qarab ishlardi (F.text.in_(...)).
Agar ikki xil rol menyusida (tasodifan yoki tarjima orqali) bir xil matn
paydo bo'lsa, qaysi router birinchi ro'yxatdan o'tgan bo'lsa, o'sha doim
ishga tushardi — masalan admin "O'quvchilar" tugmasini bossa, aslida
teacher (o'qituvchi) handleriga tushib, xato/tushunarsiz javob berardi.

RoleIs filtri buni matn filtridan KEYIN tekshiradi (arzon narsa oldin):
rol mos kelmasa, aiogram avtomatik navbatdagi routerga o'tkazadi —
hech qanday "tushunmadim" xatosiz, to'g'ri rol handleriga yetib boradi.
"""

from aiogram.filters import BaseFilter
from aiogram.types import Message

from bot.utils.db_helpers import resolve_user


class RoleIs(BaseFilter):
    def __init__(self, *roles: str):
        self.roles = set(roles)

    def __call__(self, message: Message) -> bool:
        if not message.from_user:
            return False
        user = resolve_user(message.from_user.id)
        return bool(user and user.get("role") in self.roles)
