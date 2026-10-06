"""Kunlik vazifalar — APScheduler."""

import asyncio
import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from bot.config import ADMIN_TG_ID
from bot.utils.db_helpers import (
    get_all_students, get_settings, get_schedule,
)
from bot.utils.helpers import lesson_num
from bot.utils.helpers import now_tashkent, today_uz, days_uz, TASHKENT_TZ

log = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


def _get_bot():
    from bot.instance import bot
    return bot


async def send_morning_schedule():
    """07:00 — Bugungi jadval guruhga."""
    try:
        s = get_settings()
        gid = s.get("classGroupId")
        if not gid:
            return
        class_id = s.get("className", "9-A")
        lessons = get_schedule(class_id)
        today = today_uz()

        today_lessons = [l for l in lessons
                         if (l.get("dayOfWeek") or l.get("day")) == today]
        if not today_lessons:
            return

        text = f"🌅 <b>Xayrli tong!</b>\n\n📅 <b>Bugun ({today}):</b>\n\n"
        for l in sorted(today_lessons,
                        key=lesson_num):
            num = lesson_num(l) or "—"
            subj = l.get("subject") or "—"
            text += f"{num}. {subj}\n"

        await _get_bot().send_message(int(gid), text)
        log.info("Ertalabki jadval yuborildi")
    except Exception as e:
        log.error("send_morning_schedule xato: %s", e)


async def send_evening_report():
    """16:00 — Adminga kunlik hisobot."""
    if not ADMIN_TG_ID:
        return
    try:
        s = get_settings()
        class_id = s.get("className", "9-A")
        students = get_all_students(class_id)

        from bot.utils.db_helpers import calc_student_stats
        total = 0
        n = 0
        for st in students:
            stats = calc_student_stats(st["id"])
            if stats["avg"] > 0:
                total += stats["avg"]
                n += 1

        avg = round(total / n, 2) if n else 0
        text = (
            f"📊 <b>Kunlik hisobot</b>\n"
            f"🗓 {now_tashkent().strftime('%d.%m.%Y')}\n\n"
            f"👥 O'quvchilar: {len(students)}\n"
            f"📈 O'rtacha: {avg}\n"
        )
        await _get_bot().send_message(ADMIN_TG_ID, text)
    except Exception as e:
        log.error("send_evening_report xato: %s", e)


async def send_homework_reminder():
    """18:00 — O'quvchilarga uy vazifasi eslatmasi."""
    try:
        s = get_settings()
        class_id = s.get("className", "9-A")
        students = get_all_students(class_id)

        for st in students:
            tg = st.get("tgId")
            if not tg:
                continue
            try:
                await _get_bot().send_message(
                    tg,
                    "📚 <b>Uy vazifasini unutmang!</b>\n"
                    "Bugungi vazifalarni tekshiring.",
                )
                await asyncio.sleep(0.3)
            except Exception:
                pass
    except Exception as e:
        log.error("send_homework_reminder xato: %s", e)


def start():
    global _scheduler
    if _scheduler:
        return _scheduler

    _scheduler = AsyncIOScheduler(timezone=TASHKENT_TZ)

    _scheduler.add_job(send_morning_schedule, CronTrigger(hour=7, minute=0),
                       id="morning_schedule")
    _scheduler.add_job(send_evening_report, CronTrigger(hour=16, minute=0),
                       id="evening_report")
    _scheduler.add_job(send_homework_reminder, CronTrigger(hour=18, minute=0),
                       id="homework_reminder")

    _scheduler.start()
    log.info("✅ Kunlik scheduler ishga tushdi")
    return _scheduler


def stop():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown()
        _scheduler = None