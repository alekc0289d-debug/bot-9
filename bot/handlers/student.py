"""O'quvchi handlerlari: baholar, jadval, davomat, uy vazifasi, reyting."""

import logging
from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

from bot.locales.loader import t
from bot.utils.btn_texts import variants
from bot.utils.db_helpers import (
    get_student_by_tg, get_grades, get_schedule, get_subjects,
    calc_student_stats, get_rating, get_recent_grades,
)
from bot.utils.role_guard import RoleIs
from bot.utils.helpers import lesson_num
from bot.utils.helpers import (
    score_emoji, format_score, get_type_label,
    days_uz, today_uz, now_tashkent,
)

log = logging.getLogger(__name__)
router = Router()

# Locale fayllaridan avtomatik — bitta manba, qo'lda ko'chirish yo'q
GRADE_BTNS = variants("btn_grades")
SCHED_BTNS = variants("btn_schedule")
ATT_BTNS = variants("btn_attendance")
HW_BTNS = variants("btn_homework")
RATE_BTNS = variants("btn_rating")
ACH_BTNS = variants("btn_achievements")

_ROLE = RoleIs("student")


def _student(message: Message):
    return get_student_by_tg(message.from_user.id)


# ============================================================
# BAHOLAR
# ============================================================
@router.message(Command("baholarim", "baholar", "grades"), _ROLE)
@router.message(F.text.in_(GRADE_BTNS), _ROLE)
async def show_grades(message: Message):
    st = _student(message)
    if not st:
        await message.answer("❌ Siz topilmadingiz. /start ni bosing.")
        return

    grades = get_grades(st["id"], limit=200)
    if not grades:
        await message.answer("📭 Hozircha baholar yo'q.")
        return

    stats = calc_student_stats(st["id"])
    text = (
        f"📊 <b>{st.get('fullName', '—')}</b>\n"
        f"🏫 {st.get('classId', '—')}\n\n"
        f"📈 O'rtacha: <b>{stats['avg']}</b>\n"
        f"📝 Jami: <b>{stats['count']}</b> ta baho\n\n"
    )

    # Oxirgi 10 ta
    text += "<b>🕒 Oxirgi baholar:</b>\n"
    for g in grades[:10]:
        emoji = score_emoji(g.get("score"))
        typ = get_type_label(g.get("markType"))
        date = g.get("date", "—")
        subj = g.get("subject", "—")
        val = format_score(g)
        text += f"{emoji} {date} | <b>{subj}</b> — {val} ({typ})\n"

    # Fan bo'yicha o'rtacha
    if stats["by_subject"]:
        text += "\n<b>📚 Fanlar bo'yicha:</b>\n"
        for subj, avg in sorted(stats["by_subject"].items(),
                                key=lambda x: -x[1])[:8]:
            text += f"• {subj}: <b>{avg}</b>\n"

    await message.answer(text)


# ============================================================
# JADVAL
# ============================================================
@router.message(Command("jadvalim", "jadval"), _ROLE)
@router.message(F.text.in_(SCHED_BTNS), _ROLE)
async def show_schedule(message: Message):
    st = _student(message)
    if not st:
        await message.answer("❌ Siz topilmadingiz. /start ni bosing.")
        return

    class_id = st.get("classId", "9-A")
    lessons = get_schedule(class_id)

    if not lessons:
        await message.answer(
            f"📅 <b>{class_id} jadvali</b>\n\n"
            "⚠️ Jadval hozircha yuklanmagan.\n"
            "Tez orada qo'shiladi."
        )
        return

    # Hafta kunlari bo'yicha guruhlash
    by_day: dict = {}
    for l in lessons:
        day = l.get("dayOfWeek") or l.get("day") or "—"
        by_day.setdefault(day, []).append(l)

    days_order = days_uz()
    today = today_uz()

    text = f"📅 <b>{class_id} — Haftalik jadval</b>\n\n"

    for day in days_order:
        if day not in by_day:
            continue
        mark = " 🔸" if day == today else ""
        text += f"<b>{day}{mark}</b>\n"
        day_lessons = sorted(by_day[day],
                             key=lesson_num)
        for l in day_lessons:
            num = lesson_num(l) or "—"
            subj = l.get("subject") or l.get("name") or "—"
            teacher = l.get("teacher", "")
            room = l.get("room") or l.get("cabinet") or ""
            line = f"  {num}. {subj}"
            if teacher:
                line += f" ({teacher})"
            if room:
                line += f" — {room}"
            text += line + "\n"
        text += "\n"

    await message.answer(text)


# ============================================================
# DAVOMAT
# ============================================================
@router.message(Command("davomatim", "davomat"), _ROLE)
@router.message(F.text.in_(ATT_BTNS), _ROLE)
async def show_attendance(message: Message):
    st = _student(message)
    if not st:
        await message.answer("❌ Siz topilmadingiz. /start ni bosing.")
        return

    # attendance kolleksiyasi bo'lsa ishlatamiz
    try:
        from firebase_client import db
        snap = list(db().collection("attendance")
                    .where("studentId", "==", st["id"])
                    .limit(100).stream())
        records = [{"id": s.id, **s.to_dict()} for s in snap]
    except Exception:
        records = []

    if not records:
        await message.answer(
            "📔 <b>Davomat</b>\n\n"
            "ℹ️ Davomat ma'lumotlari hozircha yuklanmagan."
        )
        return

    records.sort(key=lambda x: x.get("date", ""), reverse=True)
    text = f"📔 <b>{st.get('fullName', '—')} — Davomat</b>\n\n"
    for r in records[:20]:
        date = r.get("date", "—")
        status = r.get("status", "—")
        emoji = {"present": "✅", "absent": "❌", "late": "⏰",
                 "excused": "🟡"}.get(status, "⚪️")
        text += f"{emoji} {date} — {status}\n"

    await message.answer(text)


# ============================================================
# UY VAZIFASI
# ============================================================
@router.message(Command("uyvazifam", "uyvazifa"), _ROLE)
@router.message(F.text.in_(HW_BTNS), _ROLE)
async def show_homework(message: Message):
    st = _student(message)
    if not st:
        await message.answer("❌ Siz topilmadingiz. /start ni bosing.")
        return

    try:
        from firebase_client import db
        class_id = st.get("classId", "9-A")
        snap = list(db().collection("homework")
                    .where("classId", "==", class_id)
                    .limit(50).stream())
        hw = [{"id": s.id, **s.to_dict()} for s in snap]
    except Exception:
        hw = []

    if not hw:
        await message.answer("📚 Hozircha uy vazifasi yo'q.")
        return

    hw.sort(key=lambda x: x.get("date", ""), reverse=True)
    text = f"📚 <b>{st.get('classId')} — Uy vazifalari</b>\n\n"
    for h in hw[:15]:
        date = h.get("date", "—")
        subj = h.get("subject", "—")
        task = h.get("task") or h.get("text") or "—"
        text += f"📖 <b>{subj}</b> ({date})\n{task}\n\n"

    await message.answer(text)


# ============================================================
# REYTING
# ============================================================
@router.message(Command("reytingim", "reyting"), _ROLE)
@router.message(F.text.in_(RATE_BTNS), _ROLE)
async def show_rating(message: Message):
    st = _student(message)
    if not st:
        await message.answer("❌ Siz topilmadingiz. /start ni bosing.")
        return

    class_id = st.get("classId", "9-A")
    rating = get_rating(class_id)

    if not rating:
        await message.answer("🏆 Reyting hozircha mavjud emas.")
        return

    # O'z o'rnini topish
    my_rank = next((i + 1 for i, r in enumerate(rating)
                    if r["id"] == st["id"]), None)

    text = f"🏆 <b>{class_id} — Reyting</b>\n\n"
    if my_rank:
        text += f"🎯 Sizning o'rningiz: <b>#{my_rank}</b>\n\n"

    medals = ["🥇", "🥈", "🥉"]
    for i, r in enumerate(rating[:10]):
        prefix = medals[i] if i < 3 else f"{i+1}."
        me = " ← <b>siz</b>" if r["id"] == st["id"] else ""
        text += f"{prefix} {r['fullName']} — <b>{r['avg']}</b>{me}\n"

    await message.answer(text)


# ============================================================
# YUTUQLAR
# ============================================================
@router.message(Command("yutuqlarim", "yutuqlar"), _ROLE)
@router.message(F.text.in_(ACH_BTNS), _ROLE)
async def show_achievements(message: Message):
    st = _student(message)
    if not st:
        await message.answer("❌ Siz topilmadingiz. /start ni bosing.")
        return

    stats = calc_student_stats(st["id"])
    text = (
        f"🎖 <b>{st.get('fullName')} — Yutuqlar</b>\n\n"
        f"📊 O'rtacha baho: <b>{stats['avg']}</b>\n"
        f"📝 Baholar soni: <b>{stats['count']}</b>\n"
        f"🔥 Eng yuqori: <b>{stats['best']}</b>\n"
    )

    badges = []
    if stats["avg"] >= 8:
        badges.append("🏅 A'lochi")
    if stats["avg"] >= 9:
        badges.append("⭐️ Ajoyib natija")
    if stats["count"] >= 50:
        badges.append("📚 Faol o'quvchi")
    if stats["best"] == 10:
        badges.append("💯 Yuz foiz")

    if badges:
        text += "\n<b>🎁 Nishonlar:</b>\n"
        for b in badges:
            text += f"• {b}\n"
    else:
        text += "\n💪 Yaxshi natijaga erishish uchun harakat qiling!"

    await message.answer(text)