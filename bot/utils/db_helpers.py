"""Firestore bilan ishlash uchun umumiy yordamchilar."""

import logging
from datetime import datetime, timezone, timedelta

from bot.config import ADMIN_TG_ID
from bot.locales.loader import set_user_lang
from firebase_client import db

log = logging.getLogger(__name__)

TASHKENT_TZ = timezone(timedelta(hours=5))


# ============================================================
# FOYDALANUVCHI
# ============================================================
def get_student(student_id: str) -> dict | None:
    try:
        doc = db().collection("students").document(student_id).get()
        if doc.exists:
            d = doc.to_dict()
            d["id"] = doc.id
            return d
    except Exception as e:
        log.error("get_student xato: %s", e)
    return None


# resolve_user har bir xabarda (LangMiddleware, RoleIs filtri, va har bir
# handler) chaqiriladi va ichida 4 tagacha ketma-ket Firestore so'rovi
# qilishi mumkin. Firebase sekinlashsa (masalan noto'g'ri kalit tufayli
# qayta-qayta urinish bo'lsa), bu BUTUN botni bir necha daqiqaga
# "qotirib" qo'yadi — chunki har bir foydalanuvchi xabari shu bitta
# funksiyadan sekin-sekin o'tadi. Shu sababli natija qisqa muddat
# (15 soniya) xotirada saqlanadi — xatolik yoki sekinlik bo'lsa ham,
# bitta foydalanuvchi ketma-ket necha marta yozsa ham faqat bitta
# haqiqiy so'rov ketadi.
_resolve_cache: dict = {}
_RESOLVE_TTL = 15  # soniya


def resolve_user(tg_id: int) -> dict | None:
    """
    Telegram ID bo'yicha foydalanuvchi va uning roli.

    Tartib: o'quvchi (tgId) -> ota-ona (parentTgId) -> o'qituvchi (staff)
    -> users kolleksiyasi. Hech biri topilmasa va tg_id ADMIN_TG_ID bo'lsa,
    admin qaytariladi. Saqlangan til avtomatik o'rnatiladi.
    """
    cached = _resolve_cache.get(tg_id)
    if cached and (datetime.now(timezone.utc) - cached[0]).total_seconds() < _RESOLVE_TTL:
        return cached[1]

    try:
        client = db()
        found = None
        for coll, field, role, lang_key in (
            ("students", "tgId", "student", "lang"),
            ("students", "parentTgId", "parent", "parentLang"),
            ("staff", "tgId", "teacher", "lang"),
            ("users", "tgId", "admin", "lang"),
        ):
            snap = list(client.collection(coll)
                        .where(field, "==", tg_id).limit(1).stream())
            if snap:
                found = snap[0].to_dict()
                found["id"] = snap[0].id
                found["_coll"] = coll
                if coll in ("students",):
                    found["role"] = role
                else:
                    found["role"] = found.get("role") or role
                if found.get(lang_key):
                    set_user_lang(tg_id, found[lang_key])
                break
        if found:
            _resolve_cache[tg_id] = (datetime.now(timezone.utc), found)
            return found
    except Exception as e:
        log.error("resolve_user xato: %s", e)
        # DIQQAT: bu yerda qaytarib YUBORMAYMIZ — pastdagi ADMIN_TG_ID
        # zaxira tekshiruvi baribir ishlashi kerak (Firestore butunlay
        # ishlamay qolganda ham admin botga kira olishi uchun).

    if ADMIN_TG_ID and tg_id == ADMIN_TG_ID:
        result = {"id": f"admin_{tg_id}", "fullName": "Admin",
                  "role": "admin", "tgId": tg_id}
        # Admin zaxira natijasini KESHLAMAYMIZ — agar Firestore tiklansa,
        # keyingi xabarda haqiqiy hujjat (masalan to'g'ri fullName) bilan
        # almashtirilishi uchun.
        return result
    # Topilmadi (va bu admin ham emas) — QISQA muddat keshlaymiz, aks
    # holda shu foydalanuvchining har bir xabari Firestore ishlamay
    # qolganda ham to'liq 4 ta so'rovni qayta-qayta sinab, botni
    # sekinlashtiraveradi.
    _resolve_cache[tg_id] = (datetime.now(timezone.utc), None)
    return None


def mark_bot_blocked(tg_id: int, blocked: bool) -> None:
    """
    Foydalanuvchi botni bloklagan/blokdan chiqargan paytda chaqiriladi
    (bot/handlers/block_tracking.py dagi my_chat_member hodisasidan, va
    xabar yuborishda "Forbidden" xatosi chiqqanda ham — ikkalasi ham
    bir xil holatni belgilaydi, Telegram hodisasi qandaydir sabab bilan
    kelmay qolgan taqdirda ham aniqlansin uchun).

    O'quvchining o'zi uchun 'botBlocked', ota-onasi uchun
    'parentBotBlocked' (xuddi shu hujjatda, chunki ota-ona alohida
    hujjatga ega emas), xodim/admin uchun 'botBlocked' maydoniga
    yoziladi.
    """
    try:
        client = db()
        for coll, field, flag in (
            ("students", "tgId", "botBlocked"),
            ("students", "parentTgId", "parentBotBlocked"),
            ("staff", "tgId", "botBlocked"),
            ("users", "tgId", "botBlocked"),
        ):
            for d in (client.collection(coll)
                      .where(field, "==", tg_id).limit(1).stream()):
                d.reference.set({flag: blocked}, merge=True)
    except Exception as e:
        log.error("mark_bot_blocked xato: %s", e)


def save_user_lang(tg_id: int, lang: str) -> None:
    """Tanlangan tilni Firestore'ga yozish (qayta ishga tushganda yo'qolmasligi uchun)."""
    try:
        client = db()
        for coll, field, key in (
            ("students", "tgId", "lang"),
            ("students", "parentTgId", "parentLang"),
            ("staff", "tgId", "lang"),
            ("users", "tgId", "lang"),
        ):
            for d in (client.collection(coll)
                      .where(field, "==", tg_id).limit(1).stream()):
                d.reference.set({key: lang}, merge=True)
    except Exception as e:
        log.error("save_user_lang xato: %s", e)


def get_student_by_tg(tg_id: int) -> dict | None:
    try:
        snap = list(db().collection("students")
                    .where("tgId", "==", tg_id).limit(1).stream())
        if snap:
            d = snap[0].to_dict()
            d["id"] = snap[0].id
            return d
    except Exception as e:
        log.error("get_student_by_tg xato: %s", e)
    return None


def get_student_by_phone(phone: str) -> dict | None:
    """Telefon orqali o'quvchi (parent uchun ham)."""
    try:
        client = db()
        for field, role in (("phone", "student"),
                            ("motherPhone", "parent"),
                            ("fatherPhone", "parent")):
            snap = list(client.collection("students")
                        .where(field, "==", phone).limit(1).stream())
            if snap:
                d = snap[0].to_dict()
                d["id"] = snap[0].id
                d["_matched_as"] = role
                return d
    except Exception as e:
        log.error("get_student_by_phone xato: %s", e)
    return None


def get_all_students(class_id: str | None = None, limit: int = 200) -> list:
    try:
        q = db().collection("students")
        if class_id:
            q = q.where("classId", "==", class_id)
        return [{"id": s.id, **s.to_dict()} for s in q.limit(limit).stream()]
    except Exception as e:
        log.error("get_all_students xato: %s", e)
    return []


# ============================================================
# BAHOLAR
# ============================================================
def get_grades(student_id: str, limit: int = 100) -> list:
    try:
        snap = (db().collection("grades")
                .where("studentId", "==", student_id)
                .limit(limit).stream())
        grades = [{"id": g.id, **g.to_dict()} for g in snap]
        grades.sort(key=lambda x: x.get("date", ""), reverse=True)
        return grades
    except Exception as e:
        log.error("get_grades xato: %s", e)
    return []


def get_grades_by_subject(student_id: str, subject: str) -> list:
    return [g for g in get_grades(student_id) if g.get("subject") == subject]


def get_recent_grades(student_id: str, days: int = 7) -> list:
    cutoff = (datetime.now(TASHKENT_TZ) - timedelta(days=days)).strftime("%Y-%m-%d")
    return [g for g in get_grades(student_id) if g.get("date", "") >= cutoff]


def get_subjects(student_id: str) -> list:
    try:
        snap = (db().collection("subjects")
                .where("studentId", "==", student_id)
                .stream())
        return [{"id": s.id, **s.to_dict()} for s in snap]
    except Exception as e:
        log.error("get_subjects xato: %s", e)
    return []


def get_schedule(class_id: str) -> list:
    """Jadval — sinf bo'yicha.

    Bir nechta saqlash shaklini qo'llab-quvvatlaydi, chunki loyihada
    sinf maydoni turli joyda turlicha nomlangan ekan ("classId" yoki
    "className"): bitta hujjat ichida "lessons" massivi, YOKI har bir
    dars alohida hujjat ("classId" YOKI "className" maydoni bilan).
    Avval eskisi bor-u BO'SH (masalan loyihada qolib ketgan bo'sh "9-A"
    hujjati) bo'lsa ham haqiqiy darslarni ko'rmay qolmasligi uchun —
    bitta hujjat FAQAT ichida haqiqatan dars bo'lsa qabul qilinadi, aks
    holda pastdagi so'rovlarga o'tiladi.
    """
    try:
        client = db()
        doc = client.collection("schedule").document(class_id).get()
        if doc.exists:
            d = doc.to_dict()
            lessons = d.get("lessons") or d.get("items") or []
            if lessons:
                return lessons

        # Har o'quvchida jadval nusxasi bor — takrorlarni olib tashlaymiz.
        # "classId" VA "className" ikkalasi bo'yicha ham qidiramiz, chunki
        # loyihaning turli qismlari turli nom ishlatgan bo'lishi mumkin.
        seen, out = set(), []
        for field in ("classId", "className"):
            snap = (client.collection("schedule")
                    .where(field, "==", class_id).stream())
            for s in snap:
                row = {"id": s.id, **s.to_dict()}
                key = (row.get("dayOfWeek"), row.get("lessonNumber"),
                       row.get("subject"), row.get("teacher"),
                       row.get("startTime"))
                if key in seen:
                    continue
                seen.add(key)
                out.append(row)
        return out
    except Exception as e:
        log.error("get_schedule xato: %s", e)
    return []


# ============================================================
# STATISTIKA
# ============================================================
def calc_student_stats(student_id: str) -> dict:
    grades = get_grades(student_id, limit=500)
    if not grades:
        return {"count": 0, "avg": 0, "best": 0, "worst": 0,
                "by_subject": {}, "by_type": {}}

    scores = []
    by_subject: dict = {}
    by_type: dict = {}

    for g in grades:
        s = g.get("score")
        if s is None:
            continue
        if isinstance(s, (int, float)):
            scores.append(s)
            subj = g.get("subject", "—")
            by_subject.setdefault(subj, []).append(s)
            mt = g.get("markType", "—")
            by_type.setdefault(mt, []).append(s)

    avg = round(sum(scores) / len(scores), 2) if scores else 0

    subj_avg = {k: round(sum(v) / len(v), 1) for k, v in by_subject.items()}
    type_avg = {k: round(sum(v) / len(v), 1) for k, v in by_type.items()}

    return {
        "count": len(grades),
        "scored": len(scores),
        "avg": avg,
        "best": max(scores) if scores else 0,
        "worst": min(scores) if scores else 0,
        "by_subject": subj_avg,
        "by_type": type_avg,
    }


# ============================================================
# SETTINGS
# ============================================================
def get_settings() -> dict:
    try:
        doc = db().collection("settings").document("general").get()
        if doc.exists:
            return doc.to_dict()
    except Exception as e:
        log.error("get_settings xato: %s", e)
    return {}


def get_class_group_id(class_id: str) -> int | None:
    s = get_settings()
    gid = s.get("classGroupId")
    if gid and s.get("className") == class_id:
        try:
            return int(gid)
        except Exception:
            return None
    return None


# ============================================================
# HAFTALIK / OYLIK BALLAR (premium tanlovi)
# ============================================================
def week_start(dt=None) -> "datetime":
    """Berilgan (yoki joriy) sananing shu haftasi dushanbasi, 00:00 (Toshkent)."""
    dt = dt or datetime.now(TASHKENT_TZ)
    dt = dt.astimezone(TASHKENT_TZ)
    monday = dt - timedelta(days=dt.weekday())
    return monday.replace(hour=0, minute=0, second=0, microsecond=0)


def weekly_ranking(class_id: str, min_grades: int = 1) -> list:
    """
    Joriy hafta (Dushanbadan bugungacha) bo'yicha o'quvchilar reytingi.

    Hech qanday alohida "reset" kerak emas — sana oralig'i har doim
    joriy haftaga qarab hisoblanadi, shuning uchun har dushanba
    avtomatik ravishda 0 dan boshlanadi.
    """
    start = week_start().strftime("%Y-%m-%d")
    today = datetime.now(TASHKENT_TZ).strftime("%Y-%m-%d")

    students = get_all_students(class_id)
    result = []
    for st in students:
        grades = [
            g for g in get_grades(st["id"], limit=500)
            if start <= g.get("date", "") <= today
            and isinstance(g.get("score"), (int, float))
        ]
        if len(grades) < min_grades:
            continue
        avg = round(sum(g["score"] for g in grades) / len(grades), 2)
        result.append({
            "id": st["id"], "fullName": st.get("fullName", "—"),
            "avg": avg, "count": len(grades),
        })
    result.sort(key=lambda x: (-x["avg"], -x["count"]))
    return result


WEEKLY_BONUS = (10, 5, 1)  # 1-, 2-, 3-o'rin


def award_weekly_bonus(ranking: list) -> list:
    """
    Haftaning top-3 o'quvchisiga oylik Premium ball qo'shadi.

    Ball 'premium_points/{studentId}_{YYYY-MM}' hujjatida yig'iladi.
    Oy almashganda hujjat ID'si o'zgaradi — shu bilan '1-kuni 0 dan
    boshlanadi' talabi alohida kod yozmasdan bajariladi.
    """
    month = datetime.now(TASHKENT_TZ).strftime("%Y-%m")
    week_label = week_start().strftime("%Y-%m-%d")
    awarded = []
    for i, bonus in enumerate(WEEKLY_BONUS):
        if i >= len(ranking):
            break
        r = ranking[i]
        doc_id = f"{r['id']}_{month}"
        try:
            ref = db().collection("premium_points").document(doc_id)
            doc = ref.get()
            data = doc.to_dict() if doc.exists else {}
            weeks = data.get("weeks", [])
            if any(w.get("week") == week_label for w in weeks):
                continue  # bu hafta uchun ball allaqachon berilgan
            weeks.append({"week": week_label, "rank": i + 1, "points": bonus,
                          "avg": r["avg"]})
            ref.set({
                "studentId": r["id"],
                "fullName": r["fullName"],
                "month": month,
                "points": data.get("points", 0) + bonus,
                "weeks": weeks[-8:],
                "updatedAt": datetime.now(timezone.utc),
            }, merge=True)
            awarded.append({**r, "rank": i + 1, "bonus": bonus})
        except Exception as e:
            log.error("award_weekly_bonus xato (%s): %s", r["id"], e)
    return awarded


def get_monthly_points(month: str | None = None) -> list:
    """Joriy (yoki berilgan YYYY-MM) oy bo'yicha to'plangan Premium ballari, kamayish tartibida."""
    month = month or datetime.now(TASHKENT_TZ).strftime("%Y-%m")
    try:
        snap = (db().collection("premium_points")
                .where("month", "==", month).stream())
        rows = [{"id": d.id.rsplit("_", 1)[0], **d.to_dict()} for d in snap]
        rows.sort(key=lambda x: (-x.get("points", 0), x.get("fullName", "")))
        return rows
    except Exception as e:
        log.error("get_monthly_points xato: %s", e)
        return []


# ============================================================
# REYTING
# ============================================================
def get_rating(class_id: str) -> list:
    """Sinf bo'yicha o'quvchilar reytingi."""
    students = get_all_students(class_id)
    result = []
    for st in students:
        stats = calc_student_stats(st["id"])
        result.append({
            "id": st["id"],
            "fullName": st.get("fullName", "—"),
            "avg": stats["avg"],
            "count": stats["count"],
        })
    result.sort(key=lambda x: x["avg"], reverse=True)
    return result