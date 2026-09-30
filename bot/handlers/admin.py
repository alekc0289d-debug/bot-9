"""Admin handlerlari."""

import asyncio
import logging
from datetime import datetime, timezone

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from bot.config import ADMIN_TG_ID
from bot.keyboards import inline
from bot.locales.loader import t
from bot.utils.btn_texts import variants
from bot.utils.db_helpers import (
    get_all_students, get_settings, get_rating, calc_student_stats,
    get_schedule, get_monthly_points,
)
from bot.utils.helpers import now_tashkent, lesson_num, days_uz, today_uz
from bot.utils.role_guard import RoleIs

log = logging.getLogger(__name__)
router = Router()


class AdminStates(StatesGroup):
    waiting_broadcast = State()
    waiting_announcement = State()


def _is_admin(message: Message) -> bool:
    return message.from_user.id == ADMIN_TG_ID


# Locale fayllaridan avtomatik — reply.py dagi tugma bilan doim mos keladi,
# va boshqa rol menyulari bilan matn to'qnashmaydi (avvalgi xato shu edi)
STUDENTS_BTNS = variants("btn_admin_students")
CLASSES_BTNS = variants("btn_admin_classes")
STAFF_BTNS = variants("btn_admin_staff")
GRADES_BTNS = variants("btn_admin_grades")
SCHED_BTNS = variants("btn_admin_schedule")
RATING_BTNS = variants("btn_admin_rating")

STATS_BTNS = variants("btn_stats")
ANN_BTNS = variants("btn_announce")
SYNC_BTNS = variants("btn_sync")
PREMIUM_BTNS = variants("btn_premium")
REPORT_BTNS = variants("btn_report")
INTRO_BTNS = variants("btn_broadcast")

_ROLE = RoleIs("admin")


def _format_full_rating(rating: list) -> str:
    text = "🏆 <b>To'liq reyting</b>\n\n"
    medals = ["🥇", "🥈", "🥉"]
    for i, r in enumerate(rating):
        prefix = medals[i] if i < 3 else f"{i+1}."
        text += f"{prefix} {r['fullName']} — <b>{r['avg']}</b> ({r['count']} baho)\n"
    return text


# ============================================================
# STATISTIKA
# ============================================================
@router.message(Command("statistika", "stats"), _ROLE)
@router.message(F.text.in_(STATS_BTNS), _ROLE)
async def admin_stats(message: Message):
    if not _is_admin(message):
        return

    s = get_settings()
    class_id = s.get("className", "9-A")
    students = get_all_students(class_id)

    text = (
        f"📊 <b>Statistika — {class_id}</b>\n\n"
        f"👥 O'quvchilar: <b>{len(students)}</b>\n"
        f"👩‍🏫 Sinf rahbari: <b>{s.get('curatorName', '—')}</b>\n"
        f"🏫 Maktab: <b>{s.get('schoolName', '—')}</b>\n\n"
    )

    # Umumiy o'rtacha
    if students:
        avgs = [calc_student_stats(st["id"])["avg"] for st in students]
        avgs = [a for a in avgs if a > 0]
        if avgs:
            overall = round(sum(avgs) / len(avgs), 2)
            text += f"📈 Sinf o'rtachasi: <b>{overall}</b>\n"
            text += f"🥇 Eng yaxshi: <b>{max(avgs)}</b>\n"
            text += f"📉 Eng past: <b>{min(avgs)}</b>\n"

    # Bot guruhlar
    from firebase_client import db
    try:
        groups = list(db().collection("bot_groups")
                      .where("active", "==", True).stream())
        text += f"\n💬 Faol guruhlar: <b>{len(groups)}</b>\n"
    except Exception:
        pass

    await message.answer(text)


# ============================================================
# E'LON
# ============================================================
@router.message(Command("elon", "announce"), _ROLE)
@router.message(F.text.in_(ANN_BTNS), _ROLE)
async def admin_announcement(message: Message, state: FSMContext):
    if not _is_admin(message):
        return
    await state.set_state(AdminStates.waiting_announcement)
    await message.answer(
        "📢 <b>E'lon yuborish</b>\n\n"
        "Matnni yozing (0 — bekor):"
    )


@router.message(AdminStates.waiting_announcement)
async def admin_announcement_send(message: Message, state: FSMContext, bot: Bot):
    if not _is_admin(message):
        await state.clear()
        return
    if not message.text:
        await message.answer("✏️ Iltimos, e'lon matnini yozing (0 — bekor).")
        return
    if message.text.strip() == "0":
        await state.clear()
        await message.answer("❌ Bekor qilindi.")
        return

    text = message.text.strip()
    s = get_settings()
    gid = s.get("classGroupId")

    # Firestore'ga saqlash
    from firebase_client import db
    try:
        db().collection("announcements").add({
            "text": text,
            "authorTgId": message.from_user.id,
            "authorName": message.from_user.full_name,
            "createdAt": datetime.now(timezone.utc),
        })
    except Exception as e:
        log.error("announcement save xato: %s", e)

    if gid:
        try:
            await bot.send_message(
                chat_id=int(gid),
                text=f"📢 <b>E'lon</b>\n\n{text}",
            )
            await message.answer("✅ E'lon saqlandi va guruhga yuborildi.")
        except Exception as e:
            await message.answer(f"⚠️ Saqlandi, lekin guruhga yuborilmadi: {e}")
    else:
        await message.answer("✅ E'lon saqlandi (guruh sozlanmagan).")

    await state.clear()


# ============================================================
# SYNC (qo'lda)
# ============================================================
@router.message(Command("sync"), _ROLE)
@router.message(F.text.in_(SYNC_BTNS), _ROLE)
async def admin_sync(message: Message):
    if not _is_admin(message):
        return

    await message.answer("🔄 Sync boshlandi... (bir necha daqiqa)")

    try:
        from firebase_client import db
        # emaktab_queue ga qo'shish
        s = get_settings()
        class_id = s.get("className", "9-A")
        students = get_all_students(class_id)

        count = 0
        for st in students:
            db().collection("emaktab_queue").document(st["id"]).set({
                "studentId": st["id"],
                "classId": class_id,
                "status": "pending",
                "requestedAt": datetime.now(timezone.utc),
                "requestedBy": message.from_user.id,
            }, merge=True)
            count += 1

        await message.answer(f"✅ {count} o'quvchi navbatga qo'shildi.")
    except Exception as e:
        await message.answer(f"❌ Xato: {e}")


# ============================================================
# PREMIUM
# ============================================================
@router.message(Command("premium"), _ROLE)
@router.message(F.text.in_(PREMIUM_BTNS), _ROLE)
async def admin_premium(message: Message):
    """
    Joriy oy uchun to'plangan Premium ballari (haftalik g'oliblarga
    dushanba/yakshanba tsikli bilan avtomatik qo'shilib boradi).
    """
    if not _is_admin(message):
        return

    points = get_monthly_points()
    month = now_tashkent().strftime("%B %Y")

    if not points:
        await message.answer(
            f"🎁 <b>Premium — {month}</b>\n\n"
            "Hali hech kimga haftalik bonus ball berilmagan.\n"
            "Ballar har yakshanba kuni avtomatik hisoblanadi."
        )
        return

    top = points[0]
    text = f"🎁 <b>Premium — {month}</b>\n\n"
    text += "<b>Joriy oy ball jadvali:</b>\n"
    for i, p in enumerate(points[:10], 1):
        text += f"{i}. {p['fullName']} — <b>{p.get('points', 0)}</b> ball\n"
    text += (
        f"\n🥇 Yetakchi: <b>{top['fullName']}</b> ({top.get('points', 0)} ball)\n"
        "Oy oxirida (31/30-kuni, 13:00) avtomatik e'lon qilinadi."
    )

    await message.answer(
        text,
        reply_markup=inline.premium_actions(top["id"]),
    )


@router.callback_query(F.data.startswith("premium:given:"))
async def premium_given(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_TG_ID:
        await callback.answer("❌ Ruxsat yo'q", show_alert=True)
        return

    student_id = callback.data.split(":")[2]
    from firebase_client import db
    try:
        db().collection("premium_history").add({
            "studentId": student_id,
            "givenAt": datetime.now(timezone.utc),
            "givenBy": callback.from_user.id,
            "month": now_tashkent().strftime("%Y-%m"),
        })
        await callback.message.edit_text("✅ Premium berildi deb belgilandi.")
    except Exception as e:
        await callback.message.edit_text(f"❌ Xato: {e}")
    await callback.answer()


@router.callback_query(F.data.startswith("premium:skip:"))
async def premium_skip(callback: CallbackQuery):
    await callback.message.edit_text("⏭ O'tkazib yuborildi.")
    await callback.answer()


@router.callback_query(F.data == "rating:full")
async def rating_full(callback: CallbackQuery):
    s = get_settings()
    rating = get_rating(s.get("className", "9-A"))
    await callback.message.answer(_format_full_rating(rating))
    await callback.answer()


# ============================================================
# O'QUVCHILAR
# ============================================================
@router.message(Command("oquvchilar"), _ROLE)
@router.message(F.text.in_(STUDENTS_BTNS), _ROLE)
async def admin_students(message: Message):
    if not _is_admin(message):
        return
    s = get_settings()
    class_id = s.get("className", "9-A")
    students = get_all_students(class_id, limit=200)

    if not students:
        await message.answer("📭 O'quvchilar topilmadi.")
        return

    students.sort(key=lambda x: x.get("fullName", ""))
    text = f"👥 <b>{class_id} — O'quvchilar</b> ({len(students)} ta)\n\n"
    for st in students[:60]:
        mark = "🤖" if st.get("tgId") else "⚪️"
        pmark = "👪" if st.get("parentTgId") else ""
        text += f"{mark}{pmark} {st.get('fullName', '—')}\n"
    if len(students) > 60:
        text += f"\n... va yana {len(students) - 60} ta"
    text += "\n\n🤖 — botga ulangan, 👪 — ota-onasi ham ulangan"

    await message.answer(text)


# ============================================================
# SINF MA'LUMOTI
# ============================================================
@router.message(Command("sinflar"), _ROLE)
@router.message(F.text.in_(CLASSES_BTNS), _ROLE)
async def admin_classes(message: Message):
    if not _is_admin(message):
        return
    s = get_settings()
    class_id = s.get("className", "9-A")
    count = len(get_all_students(class_id))

    text = (
        f"🏫 <b>Sinf ma'lumoti</b>\n\n"
        f"📛 Sinf: <b>{class_id}</b>\n"
        f"👥 O'quvchilar soni: <b>{count}</b>\n"
        f"👩‍🏫 Sinf rahbari: <b>{s.get('curatorName', '—')}</b>\n"
        f"📱 Rahbar telefoni: <b>{s.get('curatorPhone', '—')}</b>\n"
        f"🏫 Maktab: <b>{s.get('schoolName', '—')}</b>\n"
        f"💬 Guruh ID: <code>{s.get('classGroupId', '—')}</code>\n"
    )
    await message.answer(text)


# ============================================================
# XODIMLAR
# ============================================================
@router.message(Command("xodimlar"), _ROLE)
@router.message(F.text.in_(STAFF_BTNS), _ROLE)
async def admin_staff(message: Message):
    if not _is_admin(message):
        return
    from firebase_client import db
    try:
        snap = list(db().collection("staff").limit(100).stream())
        staff = [{"id": s.id, **s.to_dict()} for s in snap]
    except Exception as e:
        log.error("admin_staff xato: %s", e)
        staff = []

    if not staff:
        await message.answer("📭 Xodimlar ro'yxati bo'sh.")
        return

    text = f"👨‍🏫 <b>Xodimlar</b> ({len(staff)} ta)\n\n"
    for s in staff[:60]:
        mark = "🤖" if s.get("tgId") else "⚪️"
        role = s.get("subject") or s.get("role") or "—"
        text += f"{mark} {s.get('fullName', '—')} — {role}\n"

    await message.answer(text)


# ============================================================
# SINF BAHOLARI (fan bo'yicha o'rtacha)
# ============================================================
@router.message(F.text.in_(GRADES_BTNS), _ROLE)
async def admin_class_grades(message: Message):
    if not _is_admin(message):
        return
    s = get_settings()
    class_id = s.get("className", "9-A")
    students = get_all_students(class_id)

    by_subject: dict = {}
    total_grades = 0
    for st in students:
        stats = calc_student_stats(st["id"])
        total_grades += stats["count"]
        for subj, avg in stats["by_subject"].items():
            by_subject.setdefault(subj, []).append(avg)

    if not by_subject:
        await message.answer("📭 Hozircha baholar yo'q.")
        return

    text = f"📊 <b>{class_id} — Fanlar bo'yicha o'rtacha</b>\n\n"
    rows = sorted(by_subject.items(), key=lambda x: -sum(x[1]) / len(x[1]))
    for subj, vals in rows:
        avg = round(sum(vals) / len(vals), 2)
        text += f"• {subj}: <b>{avg}</b>\n"
    text += f"\n📝 Jami baholar: <b>{total_grades}</b>"

    await message.answer(text)


# ============================================================
# SINF JADVALI
# ============================================================
@router.message(F.text.in_(SCHED_BTNS), _ROLE)
async def admin_class_schedule(message: Message):
    if not _is_admin(message):
        return
    s = get_settings()
    class_id = s.get("className", "9-A")
    lessons = get_schedule(class_id)

    if not lessons:
        await message.answer(f"📅 {class_id} jadvali hozircha yuklanmagan.")
        return

    by_day: dict = {}
    for l in lessons:
        day = l.get("dayOfWeek") or l.get("day") or "—"
        by_day.setdefault(day, []).append(l)

    today = today_uz()
    text = f"📅 <b>{class_id} — Haftalik jadval</b>\n\n"
    for day in days_uz():
        if day not in by_day:
            continue
        mark = " 🔸" if day == today else ""
        text += f"<b>{day}{mark}</b>\n"
        for l in sorted(by_day[day], key=lesson_num):
            num = lesson_num(l) or "—"
            subj = l.get("subject") or "—"
            teacher = l.get("teacher", "")
            line = f"  {num}. {subj}"
            if teacher:
                line += f" ({teacher})"
            text += line + "\n"
        text += "\n"

    await message.answer(text)


# ============================================================
# SINF REYTINGI
# ============================================================
@router.message(F.text.in_(RATING_BTNS), _ROLE)
async def admin_class_rating(message: Message):
    if not _is_admin(message):
        return
    s = get_settings()
    rating = get_rating(s.get("className", "9-A"))
    if not rating:
        await message.answer("🏆 Reyting hozircha mavjud emas.")
        return
    await message.answer(_format_full_rating(rating))


# ============================================================
# BOTNI TANISHTIRISH (guruhga qayta yuborish)
# ============================================================
@router.message(F.text.in_(INTRO_BTNS), _ROLE)
async def admin_intro(message: Message):
    if not _is_admin(message):
        return
    s = get_settings()
    if not s.get("classGroupId"):
        await message.answer(
            "❌ Sinf guruhi sozlanmagan (settings.classGroupId).\n"
            "Bot guruhga qo'shilganda o'zi avtomatik tanishadi."
        )
        return
    await message.answer(
        "📤 Botni tanishtirish xabari sinf guruhiga qayta yuborilsinmi?",
        reply_markup=inline.admin_broadcast_confirm(),
    )


@router.callback_query(F.data == "intro:send")
async def admin_intro_send(callback: CallbackQuery, bot: Bot):
    if callback.from_user.id != ADMIN_TG_ID:
        await callback.answer("❌ Ruxsat yo'q", show_alert=True)
        return
    s = get_settings()
    gid = s.get("classGroupId")
    if not gid:
        await callback.message.edit_text("❌ Guruh sozlanmagan.")
        await callback.answer()
        return
    try:
        from bot.handlers.group import INTRO_TEXT
        me = await bot.get_me()
        await bot.send_message(
            int(gid), INTRO_TEXT,
            reply_markup=inline.intro_start_button(me.username),
            disable_web_page_preview=True,
        )
        await callback.message.edit_text("✅ Guruhga yuborildi.")
    except Exception as e:
        log.error("intro yuborish xato: %s", e)
        await callback.message.edit_text(f"❌ Xato: {e}")
    await callback.answer()


@router.callback_query(F.data == "intro:cancel")
async def admin_intro_cancel(callback: CallbackQuery):
    await callback.message.edit_text("❌ Bekor qilindi.")
    await callback.answer()


# ============================================================
# BROADCAST
# ============================================================
@router.message(Command("broadcast"), _ROLE)
async def admin_broadcast(message: Message, state: FSMContext):
    """Barcha guruhlarga erkin matn yuborish (faqat /broadcast buyrug'i orqali)."""
    if not _is_admin(message):
        return
    await state.set_state(AdminStates.waiting_broadcast)
    await message.answer("📣 Barcha guruhlarga yuboriladigan xabar matnini yozing (0 — bekor):")


@router.message(AdminStates.waiting_broadcast)
async def admin_broadcast_send(message: Message, state: FSMContext, bot: Bot):
    if not _is_admin(message):
        await state.clear()
        return
    if not message.text:
        await message.answer("✏️ Iltimos, xabar matnini yozing (0 — bekor).")
        return
    text = message.text.strip()
    if text == "0":
        await state.clear()
        await message.answer("❌ Bekor.")
        return

    from firebase_client import db
    groups = list(db().collection("bot_groups")
                  .where("active", "==", True).stream())

    sent, failed = 0, 0
    for g in groups:
        d = g.to_dict()
        try:
            await bot.send_message(d["chatId"], text)
            sent += 1
            await asyncio.sleep(0.5)
        except Exception as e:
            log.warning("Broadcast %s: %s", d.get("chatId"), e)
            failed += 1

    await message.answer(f"✅ Yuborildi: {sent}, xato: {failed}")
    await state.clear()


# ============================================================
# HISOBOT
# ============================================================
@router.message(Command("hisobot", "report"), _ROLE)
@router.message(F.text.in_(REPORT_BTNS), _ROLE)
async def admin_report(message: Message):
    if not _is_admin(message):
        return

    s = get_settings()
    class_id = s.get("className", "9-A")
    students = get_all_students(class_id)

    text = f"📄 <b>{class_id} — Hisobot</b>\n"
    text += f"🗓 {now_tashkent().strftime('%d.%m.%Y')}\n\n"

    total_grades = 0
    total_avg = 0
    n = 0
    for st in students:
        stats = calc_student_stats(st["id"])
        total_grades += stats["count"]
        if stats["avg"] > 0:
            total_avg += stats["avg"]
            n += 1

    text += f"👥 O'quvchilar: <b>{len(students)}</b>\n"
    text += f"📝 Jami baholar: <b>{total_grades}</b>\n"
    if n:
        text += f"📈 O'rtacha: <b>{round(total_avg / n, 2)}</b>\n"

    await message.answer(text)