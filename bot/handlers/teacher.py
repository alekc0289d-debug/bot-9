"""O'qituvchi handlerlari."""

import logging
from datetime import datetime

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from bot.locales.loader import t
from bot.utils.btn_texts import variants
from bot.utils.db_helpers import (
    get_all_students, get_settings, get_student_by_tg, calc_student_stats,
    get_schedule,
)
from bot.utils.helpers import now_tashkent, lesson_num, days_uz, today_uz
from bot.utils.role_guard import RoleIs

log = logging.getLogger(__name__)
router = Router()


class TeacherStates(StatesGroup):
    waiting_announcement = State()
    waiting_grade_class = State()
    waiting_grade_student = State()
    waiting_grade_subject = State()
    waiting_grade_value = State()


# Locale fayllaridan avtomatik — reply.py dagi tugma bilan doim mos keladi
CLASSES_BTNS = variants("btn_classes")
STUDENTS_BTNS = variants("btn_students")
ATT_BTNS = variants("btn_mark_attendance")
GRADE_BTNS = variants("btn_mark_grade")
HW_BTNS = variants("btn_teacher_homework")
SCHED_BTNS = variants("btn_teacher_schedule")
ANN_BTNS = variants("btn_announce")
STATS_BTNS = variants("btn_stats")

_ROLE = RoleIs("teacher")


def _teacher(message: Message):
    from firebase_client import db
    try:
        snap = list(db().collection("staff")
                    .where("tgId", "==", message.from_user.id)
                    .limit(1).stream())
        if snap:
            d = snap[0].to_dict()
            d["id"] = snap[0].id
            return d
    except Exception:
        pass
    return None


# ============================================================
# SINFLAR
# ============================================================
@router.message(F.text.in_(CLASSES_BTNS), _ROLE)
async def show_classes(message: Message):
    t_ = _teacher(message)
    if not t_:
        await message.answer("❌ Siz o'qituvchi sifatida topilmadingiz.")
        return

    classes = t_.get("classes") or ["9-A"]
    if isinstance(classes, str):
        classes = [classes]

    text = "🏫 <b>Sizning sinflaringiz:</b>\n\n"
    for c in classes:
        students = get_all_students(c)
        text += f"• <b>{c}</b> — {len(students)} o'quvchi\n"

    await message.answer(text)


# ============================================================
# O'QUVCHILAR (sinf bo'yicha)
# ============================================================
@router.message(F.text.in_(STUDENTS_BTNS), _ROLE)
async def show_students(message: Message):
    t_ = _teacher(message)
    classes = (t_ or {}).get("classes") or ["9-A"]
    if isinstance(classes, str):
        classes = [classes]

    class_id = classes[0]
    students = get_all_students(class_id)

    if not students:
        await message.answer(f"❌ {class_id} da o'quvchilar topilmadi.")
        return

    text = f"👥 <b>{class_id} — O'quvchilar ({len(students)}):</b>\n\n"
    for i, s in enumerate(students, 1):
        text += f"{i}. {s.get('fullName', '—')}\n"

    await message.answer(text)


# ============================================================
# BAHOLASH (FSM)
# ============================================================
@router.message(F.text.in_(GRADE_BTNS), _ROLE)
async def start_grading(message: Message, state: FSMContext):
    t_ = _teacher(message)
    if not t_:
        await message.answer("❌ Ruxsat yo'q.")
        return

    classes = t_.get("classes") or ["9-A"]
    if isinstance(classes, str):
        classes = [classes]

    await state.update_data(classes=classes)
    await state.set_state(TeacherStates.waiting_grade_class)

    text = "✏️ <b>Baholash</b>\n\nQaysi sinf? Raqam bilan yozing:\n\n"
    for i, c in enumerate(classes, 1):
        text += f"{i}. {c}\n"

    await message.answer(text)


@router.message(TeacherStates.waiting_grade_class)
async def grade_choose_class(message: Message, state: FSMContext):
    data = await state.get_data()
    classes = data["classes"]
    try:
        idx = int(message.text.strip()) - 1
        class_id = classes[idx]
    except Exception:
        await message.answer("❌ Noto'g'ri. Qaytadan raqam kiriting.")
        return

    students = get_all_students(class_id)
    if not students:
        await message.answer("❌ O'quvchilar yo'q.")
        await state.clear()
        return

    await state.update_data(class_id=class_id, students=students)
    await state.set_state(TeacherStates.waiting_grade_student)

    text = f"✏️ <b>{class_id}</b> — O'quvchi:\n\n"
    for i, s in enumerate(students, 1):
        text += f"{i}. {s.get('fullName')}\n"
    text += "\nRaqamni kiriting (yoki 0 — bekor):"

    await message.answer(text)


@router.message(TeacherStates.waiting_grade_student)
async def grade_choose_student(message: Message, state: FSMContext):
    if message.text.strip() == "0":
        await state.clear()
        await message.answer("❌ Bekor qilindi.")
        return

    data = await state.get_data()
    students = data["students"]
    try:
        idx = int(message.text.strip()) - 1
        st = students[idx]
    except Exception:
        await message.answer("❌ Noto'g'ri raqam.")
        return

    await state.update_data(student=st)
    await state.set_state(TeacherStates.waiting_grade_subject)
    await message.answer(
        f"👤 <b>{st.get('fullName')}</b>\n\n"
        "Fan nomini yozing (masalan: Algebra):"
    )


@router.message(TeacherStates.waiting_grade_subject)
async def grade_subject(message: Message, state: FSMContext):
    await state.update_data(subject=message.text.strip())
    await state.set_state(TeacherStates.waiting_grade_value)
    await message.answer("📊 Bahoni kiriting (1-10):")


@router.message(TeacherStates.waiting_grade_value)
async def grade_value(message: Message, state: FSMContext):
    try:
        score = int(message.text.strip())
        assert 1 <= score <= 10
    except Exception:
        await message.answer("❌ 1 dan 10 gacha raqam kiriting.")
        return

    data = await state.get_data()
    st = data["student"]
    subject = data["subject"]

    from firebase_client import db
    from datetime import timezone
    try:
        doc_id = f"manual_{st['id']}_{int(datetime.now().timestamp())}"
        db().collection("grades").document(doc_id).set({
            "studentId": st["id"],
            "subject": subject,
            "score": score,
            "rawValue": str(score),
            "maxValue": 10,
            "isPercent": False,
            "markType": "DJ",
            "source": "teacher_manual",
            "date": now_tashkent().strftime("%Y-%m-%d"),
            "dayOfWeek": now_tashkent().strftime("%A"),
            "createdAt": datetime.now(timezone.utc),
            "teacherTgId": message.from_user.id,
        })
        await message.answer(
            f"✅ Baho qo'yildi!\n\n"
            f"👤 {st.get('fullName')}\n"
            f"📖 {subject}: <b>{score}</b>"
        )
    except Exception as e:
        log.error("grade_value xato: %s", e)
        await message.answer(f"❌ Xato: {e}")

    await state.clear()


# ============================================================
# DAVOMAT
# ============================================================
@router.message(F.text.in_(ATT_BTNS), _ROLE)
async def attendance_start(message: Message):
    t_ = _teacher(message)
    if not t_:
        await message.answer("❌ Ruxsat yo'q.")
        return
    await message.answer(
        "✅ <b>Davomat</b>\n\n"
        "ℹ️ Davomat funksiyasi hozircha sayt orqali amalga oshiriladi.\n"
        "Tez orada botga ham qo'shiladi."
    )


# ============================================================
# UY VAZIFA
# ============================================================
@router.message(F.text.in_(HW_BTNS), _ROLE)
async def homework_start(message: Message):
    if not _teacher(message):
        await message.answer("❌ Ruxsat yo'q.")
        return
    await message.answer(
        "📚 <b>Uy vazifasi</b>\n\n"
        "Uy vazifasini sayt orqali kiriting.\n"
        "Tez orada botga ham qo'shiladi."
    )


# ============================================================
# E'LON YUBORISH
# ============================================================
@router.message(F.text.in_(ANN_BTNS), _ROLE)
async def announcement_start(message: Message, state: FSMContext):
    t_ = _teacher(message)
    if not t_:
        await message.answer("❌ Ruxsat yo'q.")
        return
    await state.set_state(TeacherStates.waiting_announcement)
    await message.answer(
        "📢 <b>E'lon yuborish</b>\n\n"
        "E'lon matnini yozing (yoki 0 — bekor):"
    )


@router.message(TeacherStates.waiting_announcement)
async def announcement_send(message: Message, state: FSMContext):
    if not _teacher(message):
        await state.clear()
        return
    if not message.text:
        await message.answer("✏️ Iltimos, matn yozing (0 — bekor).")
        return
    if message.text.strip() == "0":
        await state.clear()
        await message.answer("❌ Bekor qilindi.")
        return

    text = message.text.strip()
    s = get_settings()
    group_id = s.get("classGroupId")

    if not group_id:
        await message.answer("❌ Guruh sozlanmagan.")
        await state.clear()
        return

    try:
        await message.bot.send_message(
            chat_id=int(group_id),
            text=f"📢 <b>E'lon</b>\n\n{text}\n\n"
                 f"— {message.from_user.full_name}",
        )
        await message.answer("✅ E'lon guruhga yuborildi.")
    except Exception as e:
        await message.answer(f"❌ Xato: {e}")

    await state.clear()


# ============================================================
# SINF JADVALI
# ============================================================
@router.message(F.text.in_(SCHED_BTNS), _ROLE)
async def teacher_schedule(message: Message):
    t_ = _teacher(message)
    classes = (t_ or {}).get("classes") or [get_settings().get("className", "9-A")]
    if isinstance(classes, str):
        classes = [classes]
    class_id = classes[0]

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
            room = l.get("room") or l.get("cabinet") or ""
            line = f"  {num}. {subj}"
            if room:
                line += f" — {room}"
            text += line + "\n"
        text += "\n"

    await message.answer(text)


# ============================================================
# STATISTIKA
# ============================================================
@router.message(F.text.in_(STATS_BTNS), _ROLE)
async def teacher_stats(message: Message):
    t_ = _teacher(message)
    classes = (t_ or {}).get("classes") or ["9-A"]
    if isinstance(classes, str):
        classes = [classes]

    text = "📊 <b>Statistika</b>\n\n"
    for c in classes:
        students = get_all_students(c)
        text += f"🏫 <b>{c}</b> — {len(students)} o'quvchi\n"
        for s in students[:5]:
            stats = calc_student_stats(s["id"])
            text += f"  • {s.get('fullName')}: {stats['avg']}\n"
        text += "\n"

    await message.answer(text)