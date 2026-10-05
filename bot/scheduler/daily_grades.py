"""Kundalik baholar hisoboti.

Har kuni soat 13:00 da (Toshkent) har bir o'quvchiga (va ota-onasiga,
agar botga ulangan bo'lsa) o'sha kuni jadvalda bo'lgan har bir fan
bo'yicha bugungi baho — yoki 'baho yo'q' — yuboriladi. Masalan:

    📅 Bugungi baholar — 29.09.2026

    Matematika: 8
    Ona tili: baho yo'q
    Tarix: 9
    Texnologiya: baho yo'q
    Informatika: baho yo'q

Agar bugun jadvalda dars bo'lmasa (masalan yakshanba), o'quvchiga shu
haqda qisqa xabar yuboriladi ("Bugun — Yakshanba, dars yo'q"), avval
bo'lgani kabi JIM qolinmaydi.

Shu moduldagi _subjects_for_day / _build_text funksiyalari
bot/handlers/student.py dagi "📅 Kunlik baholar" (istalgan hafta
kunini tanlash) funksiyasida ham qayta ishlatiladi.
"""

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from aiogram.exceptions import TelegramForbiddenError

from bot.locales.loader import t
from bot.utils.db_helpers import get_all_students, get_schedule, get_grades, get_settings, mark_bot_blocked
from bot.utils.helpers import lesson_num, today_uz, now_tashkent

log = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


def _get_bot():
    from bot.instance import bot
    return bot


async def _safe_send(bot, tg_id: int, text: str) -> bool:
    """Xabar yuborishda 'Forbidden' (bloklagan) xatosini alohida tutadi
    va Firestore'ga yozadi — my_chat_member hodisasi negadir kelmay
    qolgan taqdirda ham, sayt holatni to'g'ri ko'rsatishi uchun."""
    try:
        await bot.send_message(int(tg_id), text)
        return True
    except TelegramForbiddenError:
        log.info("%s botni bloklagan — belgilandi", tg_id)
        mark_bot_blocked(int(tg_id), True)
        return False
    except Exception as e:
        log.warning("daily_grades %s ga yuborilmadi: %s", tg_id, e)
        return False


def _subjects_for_day(class_id: str, day_name: str) -> list:
    """Berilgan hafta kunidagi fanlar, dars tartibi bo'yicha, takrorlarsiz."""
    lessons = [
        l for l in get_schedule(class_id)
        if (l.get("dayOfWeek") or l.get("day")) == day_name
    ]
    lessons.sort(key=lesson_num)
    seen, subjects = set(), []
    for l in lessons:
        subj = l.get("subject") or l.get("name")
        if subj and subj not in seen:
            seen.add(subj)
            subjects.append(subj)
    return subjects


def _today_subjects(class_id: str) -> list:
    return _subjects_for_day(class_id, today_uz())


def _build_text(student_id: str, subjects: list, date_str: str, tg_id: int,
                 date_label: str | None = None, title: str | None = None) -> str:
    day_grades = [g for g in get_grades(student_id, limit=200)
                  if g.get("date") == date_str]
    by_subject: dict = {}
    for g in day_grades:
        by_subject.setdefault(g.get("subject"), []).append(g)

    label = date_label or now_tashkent().strftime("%d.%m.%Y")
    header = title or f"📅 <b>Bugungi baholar — {label}</b>"
    lines = [header, ""]
    for subj in subjects:
        grades = by_subject.get(subj)
        if grades:
            vals = ", ".join(str(g.get("score", g.get("rawValue", "—"))) for g in grades)
            lines.append(f"{subj}: <b>{vals}</b>")
        else:
            lines.append(f"{subj}: {t('no_grade_today', tg_id=tg_id)}")
    return "\n".join(lines)


async def daily_grades_report():
    """Soat 13:00 — bugungi baholar (yoki 'baho yo'q') har o'quvchiga.

    Bugun jadvalda dars bo'lmasa ham (masalan yakshanba), qisqa xabar
    yuboriladi — avvalgidek JIM qolinmaydi.
    """
    try:
        s = get_settings()
        class_id = s.get("className", "9-A")
        date_str = now_tashkent().strftime("%Y-%m-%d")
        today_name = today_uz()

        subjects = _today_subjects(class_id)
        students = get_all_students(class_id)
        bot = _get_bot()
        sent = 0

        if not subjects:
            text = (
                f"📅 <b>Bugun — {today_name}</b>\n\n"
                "Bugun jadvalda dars yo'q."
            )
            for st in students:
                for tg_id in (st.get("tgId"), st.get("parentTgId")):
                    if not tg_id:
                        continue
                    if await _safe_send(bot, tg_id, text):
                        sent += 1
                    await asyncio.sleep(0.05)
            log.info("daily_grades_report: dars yo'q xabari %s ta yuborildi", sent)
            return

        for st in students:
            text = _build_text(st["id"], subjects, date_str, st.get("tgId"))

            for tg_id in (st.get("tgId"), st.get("parentTgId")):
                if not tg_id:
                    continue
                if await _safe_send(bot, tg_id, text):
                    sent += 1
                await asyncio.sleep(0.05)  # Telegram flood limitidan saqlanish

        log.info("daily_grades_report: %s ta xabar yuborildi", sent)
    except Exception as e:
        log.error("daily_grades_report xato: %s", e)


def start():
    global _scheduler
    if _scheduler:
        return _scheduler

    _scheduler = AsyncIOScheduler(timezone="Asia/Tashkent")
    _scheduler.add_job(daily_grades_report, CronTrigger(hour=13, minute=0),
                       id="daily_grades_report")
    _scheduler.start()
    log.info("✅ Kundalik baholar scheduleri ishga tushdi")
    return _scheduler


def stop():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown()
        _scheduler = None
