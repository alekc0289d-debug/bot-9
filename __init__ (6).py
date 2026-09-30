"""Haftalik vazifalar — bonus ballar va haftalik hisobot.

Har yakshanba kuni (20:00, Toshkent) shu haftaning (Dushanbadan
bugungacha) eng yaxshi 3 o'quvchisiga oylik Premium tanlovi uchun
bonus ball beriladi: 1-o'rin +10, 2-o'rin +5, 3-o'rin +1.

Alohida "dushanba kuni 0 dan boshlash" kodi kerak emas — reyting
har doim FAQAT joriy haftaning baholaridan hisoblanadi
(bot.utils.db_helpers.weekly_ranking), shuning uchun har dushanba
avtomatik ravishda "0 dan" boshlanadi.
"""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from bot.config import ADMIN_TG_ID
from bot.utils.db_helpers import (
    get_settings, weekly_ranking, award_weekly_bonus,
)

log = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


def _get_bot():
    from bot.instance import bot
    return bot


async def weekly_bonus_and_report():
    """Yakshanba 20:00 — bonus ballarni berish va sinf guruhiga e'lon qilish."""
    try:
        s = get_settings()
        class_id = s.get("className", "9-A")
        group_id = s.get("classGroupId")

        ranking = weekly_ranking(class_id)
        if not ranking:
            log.info("weekly_bonus: bu hafta hech kim baho olmagan")
            return

        awarded = award_weekly_bonus(ranking)

        text = "📊 <b>Haftalik reyting</b>\n\n"
        medals = ["🥇", "🥈", "🥉"]
        for i, r in enumerate(ranking[:10]):
            prefix = medals[i] if i < 3 else f"{i+1}."
            bonus = ""
            if i < 3:
                pts = (10, 5, 1)[i]
                bonus = f" (+{pts} ball 🎁)"
            text += f"{prefix} {r['fullName']} — <b>{r['avg']}</b>{bonus}\n"

        if awarded:
            text += (
                "\n🎁 Yuqoridagi 3 nafar o'quvchiga oylik <b>Premium</b> "
                "tanlovi uchun bonus ball qo'shildi."
            )

        if group_id:
            try:
                await _get_bot().send_message(int(group_id), text)
            except Exception as e:
                log.error("weekly report guruhga yuborilmadi: %s", e)

        if ADMIN_TG_ID:
            try:
                await _get_bot().send_message(ADMIN_TG_ID, text)
            except Exception as e:
                log.error("weekly report adminga yuborilmadi: %s", e)
    except Exception as e:
        log.error("weekly_bonus_and_report xato: %s", e)


async def monday_schedule():
    """Dushanba 08:00 — haftalik dars jadvali."""
    try:
        s = get_settings()
        gid = s.get("classGroupId")
        if not gid:
            return
        from bot.utils.db_helpers import get_schedule
        from bot.utils.helpers import days_uz, lesson_num
        lessons = get_schedule(s.get("className", "9-A"))
        if not lessons:
            return

        text = "📅 <b>Haftalik jadval</b>\n\n"
        by_day: dict = {}
        for l in lessons:
            day = l.get("dayOfWeek") or l.get("day") or "—"
            by_day.setdefault(day, []).append(l)

        for day in days_uz():
            if day not in by_day:
                continue
            text += f"<b>{day}</b>\n"
            for l in sorted(by_day[day], key=lesson_num):
                text += f"  {lesson_num(l) or '—'}. {l.get('subject')}\n"
            text += "\n"

        await _get_bot().send_message(int(gid), text)
    except Exception as e:
        log.error("monday_schedule xato: %s", e)


def start():
    global _scheduler
    if _scheduler:
        return _scheduler

    _scheduler = AsyncIOScheduler(timezone="Asia/Tashkent")
    _scheduler.add_job(monday_schedule, CronTrigger(day_of_week="mon", hour=8),
                       id="monday_schedule")
    _scheduler.add_job(weekly_bonus_and_report,
                       CronTrigger(day_of_week="sun", hour=20),
                       id="weekly_bonus_and_report")
    _scheduler.start()
    log.info("✅ Haftalik scheduler ishga tushdi")
    return _scheduler


def stop():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown()
        _scheduler = None
