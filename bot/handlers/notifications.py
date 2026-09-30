"""Avtomatik xabarnomalar — grade, attendance."""

import logging
from datetime import datetime, timezone

from aiogram import Bot

from bot.utils.helpers import score_emoji, format_score, get_type_label

log = logging.getLogger(__name__)


async def notify_grade(bot: Bot, student: dict, grade: dict):
    """Yangi baho haqida ota-onaga xabar."""
    parent_tg = student.get("parentTgId") or student.get("motherTgId") \
        or student.get("fatherTgId")
    if not parent_tg:
        return

    emoji = score_emoji(grade.get("score"))
    typ = get_type_label(grade.get("markType"))
    text = (
        f"🔔 <b>Yangi baho!</b>\n\n"
        f"👦 {student.get('fullName', '—')}\n"
        f"📖 {grade.get('subject', '—')}\n"
        f"{emoji} Baho: <b>{format_score(grade)}</b>\n"
        f"🏷 Tur: {typ}\n"
        f"📅 {grade.get('date', '—')}"
    )

    try:
        await bot.send_message(parent_tg, text)
        log.info("Grade xabarnoma yuborildi: %s → %s",
                 student.get("id"), parent_tg)
    except Exception as e:
        log.warning("notify_grade xato: %s", e)


async def notify_attendance(bot: Bot, student: dict, status: str, date: str):
    """Davomat haqida ota-onaga xabar."""
    parent_tg = student.get("parentTgId") or student.get("motherTgId") \
        or student.get("fatherTgId")
    if not parent_tg:
        return

    emoji = {"present": "✅", "absent": "❌",
             "late": "⏰", "excused": "🟡"}.get(status, "⚪️")
    text = (
        f"{emoji} <b>Davomat</b>\n\n"
        f"👦 {student.get('fullName', '—')}\n"
        f"📅 {date}\n"
        f"Holat: <b>{status}</b>"
    )
    try:
        await bot.send_message(parent_tg, text)
    except Exception as e:
        log.warning("notify_attendance xato: %s", e)


async def notify_homework(bot: Bot, student: dict, homework: dict):
    """Yangi uy vazifasi haqida o'quvchiga xabar."""
    tg = student.get("tgId")
    if not tg:
        return
    text = (
        f"📚 <b>Yangi uy vazifasi</b>\n\n"
        f"📖 {homework.get('subject', '—')}\n"
        f"📝 {homework.get('task', '—')}\n"
        f"📅 Muddat: {homework.get('date', '—')}"
    )
    try:
        await bot.send_message(tg, text)
    except Exception as e:
        log.warning("notify_homework xato: %s", e)


async def notify_admin(bot: Bot, admin_tg: int, text: str):
    try:
        await bot.send_message(admin_tg, text)
    except Exception as e:
        log.warning("notify_admin xato: %s", e)