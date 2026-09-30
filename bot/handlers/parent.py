"""Ota-ona handlerlari."""

import logging

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

from bot.locales.loader import t
from bot.utils.btn_texts import variants
from bot.utils.db_helpers import (
    get_student_by_tg, get_grades, get_schedule, calc_student_stats,
    get_recent_grades,
)
from bot.utils.role_guard import RoleIs
from bot.utils.helpers import lesson_num
from bot.utils.helpers import score_emoji, format_score, get_type_label

log = logging.getLogger(__name__)
router = Router()

# Locale fayllaridan avtomatik — reply.py dagi tugma bilan doim mos keladi
CHILD_BTNS = variants("btn_child")
PARENT_GRADES = variants("btn_parent_grades")
PARENT_ATT = variants("btn_parent_attendance")
PARENT_SCHED = variants("btn_parent_schedule")
PARENT_RATE = variants("btn_parent_rating")
PARENT_PAY = variants("btn_payments")
PARENT_CONTACT = variants("btn_contact")

_ROLE = RoleIs("parent")


def _child(message: Message):
    """Ota-onaning farzandini topish (o'z tgId si yoki telefon orqali)."""
    # Avval tgId bo'yicha student
    st = get_student_by_tg(message.from_user.id)
    if st:
        return st
    # keyin parent sifatida bog'langan
    from firebase_client import db
    try:
        snap = list(db().collection("students")
                    .where("parentTgId", "==", message.from_user.id)
                    .limit(1).stream())
        if snap:
            d = snap[0].to_dict()
            d["id"] = snap[0].id
            return d
    except Exception:
        pass
    return None


# ============================================================
# FARZANDIM
# ============================================================
@router.message(Command("farzandim"), _ROLE)
@router.message(F.text.in_(CHILD_BTNS), _ROLE)
async def show_child(message: Message):
    st = _child(message)
    if not st:
        await message.answer(
            "❌ Farzandingiz topilmadi.\n"
            "Iltimos, /start orqali ro'yxatdan o'ting."
        )
        return

    stats = calc_student_stats(st["id"])
    recent = get_recent_grades(st["id"], days=7)

    text = (
        f"👦 <b>{st.get('fullName', '—')}</b>\n"
        f"🏫 Sinf: {st.get('classId', '—')}\n\n"
        f"📈 O'rtacha baho: <b>{stats['avg']}</b>\n"
        f"📝 Jami baholar: <b>{stats['count']}</b>\n\n"
    )

    if recent:
        text += "🕒 <b>So'nggi 7 kun:</b>\n"
        for g in recent[:5]:
            emoji = score_emoji(g.get("score"))
            text += (f"{emoji} {g.get('date')} — {g.get('subject')}: "
                     f"<b>{format_score(g)}</b>\n")
    else:
        text += "ℹ️ So'nggi 7 kunda yangi baho yo'q."

    await message.answer(text)


# ============================================================
# FARZAND BAHOLARI
# ============================================================
@router.message(Command("baholar"), _ROLE)
@router.message(F.text.in_(PARENT_GRADES), _ROLE)
async def show_child_grades(message: Message):
    st = _child(message)
    if not st:
        await message.answer("❌ Farzandingiz topilmadi.")
        return

    grades = get_grades(st["id"], limit=100)
    if not grades:
        await message.answer("📭 Baholar yo'q.")
        return

    stats = calc_student_stats(st["id"])
    text = (
        f"📊 <b>{st.get('fullName')} — Baholar</b>\n\n"
        f"📈 O'rtacha: <b>{stats['avg']}</b>\n\n"
        "<b>🕒 Oxirgi 10 ta:</b>\n"
    )
    for g in grades[:10]:
        emoji = score_emoji(g.get("score"))
        typ = get_type_label(g.get("markType"))
        text += (f"{emoji} {g.get('date')} | {g.get('subject')} — "
                 f"<b>{format_score(g)}</b> ({typ})\n")

    await message.answer(text)


# ============================================================
# FARZAND DAVOMATI
# ============================================================
@router.message(F.text.in_(PARENT_ATT), _ROLE)
async def show_child_attendance(message: Message):
    st = _child(message)
    if not st:
        await message.answer("❌ Farzandingiz topilmadi.")
        return

    from firebase_client import db
    try:
        snap = list(db().collection("attendance")
                    .where("studentId", "==", st["id"])
                    .limit(60).stream())
        records = [{"id": s.id, **s.to_dict()} for s in snap]
    except Exception:
        records = []

    if not records:
        await message.answer("📔 Davomat ma'lumotlari hozircha yo'q.")
        return

    records.sort(key=lambda x: x.get("date", ""), reverse=True)
    present = sum(1 for r in records if r.get("status") == "present")
    absent = sum(1 for r in records if r.get("status") == "absent")

    text = (
        f"📔 <b>{st.get('fullName')} — Davomat</b>\n\n"
        f"✅ Kelgan: <b>{present}</b>\n"
        f"❌ Kelmagan: <b>{absent}</b>\n\n"
        "<b>So'nggi yozuvlar:</b>\n"
    )
    for r in records[:15]:
        status = r.get("status", "—")
        emoji = {"present": "✅", "absent": "❌", "late": "⏰",
                 "excused": "🟡"}.get(status, "⚪️")
        text += f"{emoji} {r.get('date')} — {status}\n"

    await message.answer(text)


# ============================================================
# FARZAND JADVALI
# ============================================================
@router.message(F.text.in_(PARENT_SCHED), _ROLE)
async def show_child_schedule(message: Message):
    st = _child(message)
    if not st:
        await message.answer("❌ Farzandingiz topilmadi.")
        return

    class_id = st.get("classId", "9-A")
    lessons = get_schedule(class_id)

    if not lessons:
        await message.answer(f"📅 {class_id} jadvali hozircha yuklanmagan.")
        return

    by_day: dict = {}
    for l in lessons:
        day = l.get("dayOfWeek") or l.get("day") or "—"
        by_day.setdefault(day, []).append(l)

    from bot.utils.helpers import days_uz, today_uz
    text = f"📅 <b>{st.get('fullName')} — {class_id}</b>\n\n"
    today = today_uz()
    for day in days_uz():
        if day not in by_day:
            continue
        mark = " 🔸" if day == today else ""
        text += f"<b>{day}{mark}</b>\n"
        for l in sorted(by_day[day], key=lesson_num):
            num = lesson_num(l) or "—"
            subj = l.get("subject") or "—"
            text += f"  {num}. {subj}\n"
        text += "\n"

    await message.answer(text)


# ============================================================
# FARZAND REYTINGI
# ============================================================
@router.message(F.text.in_(PARENT_RATE), _ROLE)
async def show_child_rating(message: Message):
    st = _child(message)
    if not st:
        await message.answer("❌ Farzandingiz topilmadi.")
        return

    from bot.utils.db_helpers import get_rating
    rating = get_rating(st.get("classId", "9-A"))
    if not rating:
        await message.answer("🏆 Reyting hozircha yo'q.")
        return

    my_rank = next((i + 1 for i, r in enumerate(rating)
                    if r["id"] == st["id"]), None)

    text = f"🏆 <b>{st.get('classId')} — Reyting</b>\n\n"
    if my_rank:
        text += f"🎯 Farzandingiz: <b>#{my_rank}</b>\n\n"

    medals = ["🥇", "🥈", "🥉"]
    for i, r in enumerate(rating[:10]):
        prefix = medals[i] if i < 3 else f"{i+1}."
        me = " ← <b>farzandingiz</b>" if r["id"] == st["id"] else ""
        text += f"{prefix} {r['fullName']} — <b>{r['avg']}</b>{me}\n"

    await message.answer(text)


# ============================================================
# TO'LOV
# ============================================================
@router.message(F.text.in_(PARENT_PAY), _ROLE)
async def show_payments(message: Message):
    st = _child(message)
    if not st:
        await message.answer("❌ Farzandingiz topilmadi.")
        return
    await message.answer(
        f"💳 <b>To'lov ma'lumotlari</b>\n\n"
        f"👦 {st.get('fullName')}\n"
        "ℹ️ To'lov tizimi hozircha ulanmagan.\n"
        "Maktab ma'muriyatiga murojaat qiling."
    )


# ============================================================
# ALOQA (o'qituvchi bilan)
# ============================================================
@router.message(F.text.in_(PARENT_CONTACT), _ROLE)
async def show_contact(message: Message):
    from bot.utils.db_helpers import get_settings
    s = get_settings()

    text = "📞 <b>Aloqa</b>\n\n"
    if s.get("curatorName"):
        text += f"👩‍🏫 Sinf rahbari: <b>{s['curatorName']}</b>\n"
    if s.get("curatorPhone"):
        text += f"📱 Telefon: <code>{s['curatorPhone']}</code>\n"
    if s.get("adminName"):
        text += f"\n👨‍💼 Admin: <b>{s['adminName']}</b>\n"
    if s.get("adminPhone"):
        text += f"📱 Telefon: <code>{s['adminPhone']}</code>\n"
    if s.get("schoolPhone"):
        text += f"\n🏫 Maktab: <code>{s['schoolPhone']}</code>\n"

    await message.answer(text)