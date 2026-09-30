"""Oylik vazifalar — Premium g'olibini e'lon qilish.

Oyning oxirgi kuni (31/30-kuni) soat 13:00 da (Toshkent) shu oy davomida
haftalik bonus ballarni eng ko'p to'plagan o'quvchi e'lon qilinadi.

- Sinf guruhiga (va o'quvchining o'ziga) YUBORILADIGAN xabarda hech qanday
  "sovg'a qilish" tugmasi bo'lmaydi — faqat matn: Premium administrator
  tomonidan tez orada beriladi va tasdiqlovchi isbot yuboriladi.
- Adminga ALOHIDA, shaxsiy xabar tugmalar bilan yuboriladi (Premium
  berdim / O'tkazib yuborish) — bu faqat adminning o'z boshqaruv paneli.

Yangi oy kelganda 1-kuni "0 dan boshlanishi" uchun alohida kod kerak
emas — ballar 'premium_points/{studentId}_{YYYY-MM}' hujjatida
saqlanadi, oy o'zgarganda hujjat ID'si ham o'zgaradi.
"""

import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from bot.config import ADMIN_TG_ID
from bot.keyboards import inline
from bot.utils.db_helpers import get_settings, get_monthly_points, get_student
from bot.utils.helpers import now_tashkent

log = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None

WINNER_NOTE = (
    "\n\n🎁 Premium administrator tomonidan tez orada beriladi va "
    "tasdiqlovchi (screenshot/rasm) yuboriladi."
)


def _get_bot():
    from bot.instance import bot
    return bot


async def find_monthly_winner():
    """Oy oxiri, 13:00 — g'olibni aniqlash va e'lon qilish."""
    try:
        s = get_settings()
        gid = s.get("classGroupId")
        month = now_tashkent().strftime("%B %Y")

        points = get_monthly_points()

        if not points:
            text = (
                f"🎁 <b>Oylik Premium — {month}</b>\n\n"
                "Bu oy hali hech kim bonus ball to'plamadi."
            )
            if gid:
                await _get_bot().send_message(int(gid), text)
            return

        top = points[0]

        # Firestore'ga yozish (admin tasdig'i uchun)
        from firebase_client import db
        try:
            db().collection("premium_candidates").document(
                now_tashkent().strftime("%Y-%m")
            ).set({
                "studentId": top["id"],
                "fullName": top["fullName"],
                "points": top.get("points", 0),
                "month": month,
                "createdAt": datetime.now(timezone.utc),
                "status": "pending",
            })
        except Exception as e:
            log.error("premium_candidates saqlash xato: %s", e)

        # 1) Sinf guruhiga / g'olibga — tugmasiz, "tez orada beriladi" matni bilan
        group_text = (
            f"🎉 <b>Oylik Premium g'olibi — {month}</b>\n\n"
            f"🥇 <b>{top['fullName']}</b>\n"
            f"⭐️ To'plagan ball: <b>{top.get('points', 0)}</b>\n\n"
            f"<b>Top 5:</b>\n"
        )
        for i, r in enumerate(points[:5], 1):
            group_text += f"{i}. {r['fullName']} — {r.get('points', 0)} ball\n"
        group_text += WINNER_NOTE

        if gid:
            try:
                await _get_bot().send_message(int(gid), group_text)
            except Exception as e:
                log.error("monthly winner guruhga yuborilmadi: %s", e)

        winner_student = get_student(top["id"])
        winner_tg = (winner_student or {}).get("tgId")
        if winner_tg:
            try:
                await _get_bot().send_message(
                    int(winner_tg),
                    f"🎉 Tabriklaymiz! Siz <b>{month}</b> oyining eng faol "
                    f"o'quvchisi bo'ldingiz!" + WINNER_NOTE,
                )
            except Exception as e:
                log.error("monthly winner o'quvchiga yuborilmadi: %s", e)

        # 2) Admin — shaxsiy panel, tugmalar bilan (faqat admin ko'radi)
        if ADMIN_TG_ID:
            admin_text = (
                f"🎁 <b>Oylik Premium g'olibi — {month}</b>\n\n"
                f"🥇 <b>{top['fullName']}</b>\n"
                f"⭐️ Ball: <b>{top.get('points', 0)}</b>\n\n"
                f"<b>Top 5:</b>\n"
            )
            for i, r in enumerate(points[:5], 1):
                admin_text += f"{i}. {r['fullName']} — {r.get('points', 0)} ball\n"

            await _get_bot().send_message(
                ADMIN_TG_ID,
                admin_text,
                reply_markup=inline.premium_actions(top["id"]),
            )
    except Exception as e:
        log.error("find_monthly_winner xato: %s", e)


async def month_end_report():
    """Oy oxiri, 20:00 — umumiy o'quv statistikasi (adminga)."""
    if not ADMIN_TG_ID:
        return
    try:
        from bot.utils.db_helpers import get_all_students, calc_student_stats
        s = get_settings()
        class_id = s.get("className", "9-A")
        students = get_all_students(class_id)

        total_avg = 0
        n = 0
        for st in students:
            stats = calc_student_stats(st["id"])
            if stats["avg"] > 0:
                total_avg += stats["avg"]
                n += 1

        text = (
            f"📊 <b>Oy yakuni</b>\n"
            f"🗓 {now_tashkent().strftime('%B %Y')}\n\n"
            f"👥 O'quvchilar: {len(students)}\n"
            f"📈 O'rtacha: {round(total_avg / n, 2) if n else 0}\n"
        )
        await _get_bot().send_message(ADMIN_TG_ID, text)
    except Exception as e:
        log.error("month_end_report xato: %s", e)


def start():
    global _scheduler
    if _scheduler:
        return _scheduler

    _scheduler = AsyncIOScheduler(timezone="Asia/Tashkent")
    # Har oyning OXIRGI kuni (28/29/30/31 — kalendarga qarab) soat 13:00
    _scheduler.add_job(find_monthly_winner, CronTrigger(day="last", hour=13),
                       id="find_monthly_winner")
    _scheduler.add_job(month_end_report, CronTrigger(day="last", hour=20),
                       id="month_end_report")
    _scheduler.start()
    log.info("✅ Oylik scheduler ishga tushdi")
    return _scheduler


def stop():
    global _scheduler
    if _scheduler:
        _scheduler.shutdown()
        _scheduler = None
