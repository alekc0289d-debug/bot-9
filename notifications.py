"""AI handlerlari — Groq integratsiyasi."""

import asyncio
import logging
from datetime import datetime, timezone

from aiogram import Router, F
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from bot.config import GROQ_API_KEY, GROQ_MODEL, AI_DAILY_LIMIT
from bot.utils.db_helpers import resolve_user, get_settings
from bot.utils.helpers import now_tashkent

log = logging.getLogger(__name__)
router = Router()


class AIStates(StatesGroup):
    chatting = State()


def _get_ai_client():
    if not GROQ_API_KEY:
        return None
    try:
        from groq import Groq
        return Groq(api_key=GROQ_API_KEY)
    except Exception as e:
        log.error("Groq client xato: %s", e)
        return None


def _system_prompt(user: dict | None, role: str = "student") -> str:
    s = get_settings()
    name = (user or {}).get("fullName", "Foydalanuvchi")
    return f"""Sen — maktab boshqaruv tizimining AI yordamchisisan.

SENING VAZIFANG:
- O'quvchilarga dars bo'yicha savollarga javob berish
- Ota-onalarga farzandi haqida ma'lumot berish
- O'qituvchilarga dars rejasi va test tuzishda yordam
- Admin uchun statistika va tahlil

QOIDALAR:
1. Faqat o'zbek tilida javob ber (rus tilida yozilsa — rus tilida).
2. Qisqa va aniq javob ber (max 300 so'z).
3. O'quvchi haqidagi ma'lumotni faqat ota-onasiga bering.
4. Boshqa foydalanuvchilarning shaxsiy ma'lumotlarini oshkor qilma.
5. Ta'limga oid savollarga to'liq javob ber.
6. Reklama, siyosat, diniy bahslarga aralashma.
7. Bilmasang — "Bilmayman" deb ayt.
8. Matematikada qadam-baqadam yechimni tushuntir.

KONTEKST:
Maktab: {s.get('schoolName', 'Maktab')}
Sinf: {s.get('className', '9-A')}
Foydalanuvchi roli: {role}
Foydalanuvchi ismi: {name}
"""


def _check_limit(tg_id: int) -> tuple[bool, int]:
    from firebase_client import db
    today = now_tashkent().strftime("%Y-%m-%d")
    doc_id = f"{tg_id}_{today}"
    try:
        doc = db().collection("ai_usage").document(doc_id).get()
        count = doc.to_dict().get("count", 0) if doc.exists else 0
        return count < AI_DAILY_LIMIT, count
    except Exception:
        return True, 0


def _get_history(tg_id: int, limit: int = 10) -> list:
    from firebase_client import db
    try:
        doc = db().collection("ai_history").document(str(tg_id)).get()
        if doc.exists:
            msgs = doc.to_dict().get("messages", [])[-limit:]
            # Groq faqat role/content qabul qiladi ("ts" maydonini olib tashlaymiz)
            return [{"role": m["role"], "content": m["content"]} for m in msgs]
    except Exception:
        pass
    return []


def _finish(tg_id: int, question: str, answer: str):
    """Tarixni saqlash va limitni ATOMIK oshirish (bitta chaqiriqda)."""
    from firebase_admin import firestore
    from firebase_client import db
    today = now_tashkent().strftime("%Y-%m-%d")
    now = datetime.now(timezone.utc)
    try:
        client = db()
        client.collection("ai_usage").document(f"{tg_id}_{today}").set({
            "tgId": tg_id,
            "date": today,
            "count": firestore.Increment(1),
            "updatedAt": now,
        }, merge=True)

        ref = client.collection("ai_history").document(str(tg_id))
        doc = ref.get()
        msgs = doc.to_dict().get("messages", []) if doc.exists else []
        ts = now.isoformat()
        msgs.append({"role": "user", "content": question, "ts": ts})
        msgs.append({"role": "assistant", "content": answer, "ts": ts})
        ref.set({"messages": msgs[-30:], "updatedAt": now}, merge=True)
    except Exception as e:
        log.error("_finish xato: %s", e)


def _generate(tg_id: int, question: str) -> str:
    """Bloklovchi qism — alohida thread'da ishlaydi (event loop qotmasligi uchun)."""
    client = _get_ai_client()
    if not client:
        raise RuntimeError("no_ai_client")
    user = resolve_user(tg_id) or {}
    role = user.get("role", "student")

    messages = [{"role": "system", "content": _system_prompt(user, role)}]
    messages.extend(_get_history(tg_id, limit=6))
    messages.append({"role": "user", "content": question})

    resp = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        temperature=0.7,
        max_tokens=800,
    )
    return resp.choices[0].message.content


async def start_ai_chat(message: Message, state: FSMContext):
    tg_id = message.from_user.id
    ok, used = await asyncio.to_thread(_check_limit, tg_id)
    if not ok:
        await message.answer(
            f"⚠️ Kunlik AI limiti tugadi ({AI_DAILY_LIMIT}/{AI_DAILY_LIMIT}).\n"
            "Ertaga qaytadan urinib ko'ring."
        )
        return

    await state.set_state(AIStates.chatting)
    await message.answer(
        f"🤖 <b>AI yordamchi</b>\n\n"
        f"Savolingizni yozing.\n"
        f"Kunlik limit: <b>{AI_DAILY_LIMIT - used}/{AI_DAILY_LIMIT}</b>\n\n"
        f"Chiqish: /stop",
    )


@router.message(Command("ai"))
async def cmd_ai(message: Message, command: CommandObject, state: FSMContext):
    if command.args:
        await _ask_ai(message, command.args)
    else:
        await start_ai_chat(message, state)


@router.message(Command("stop", "exit"))
async def cmd_stop(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("✅ AI sessiyasi tugadi.")


@router.message(AIStates.chatting, F.text)
async def ai_message(message: Message, state: FSMContext):
    await _ask_ai(message, message.text)


async def _ask_ai(message: Message, question: str):
    tg_id = message.from_user.id
    question = (question or "").strip()
    if not question:
        return
    question = question[:2000]  # juda uzun matnlardan himoya

    ok, used = await asyncio.to_thread(_check_limit, tg_id)
    if not ok:
        await message.answer(
            f"⚠️ Kunlik limit tugadi ({AI_DAILY_LIMIT}/{AI_DAILY_LIMIT})."
        )
        return

    if not GROQ_API_KEY:
        await message.answer("❌ AI xizmati hozircha sozlanmagan.")
        return

    msg = await message.answer("🤔 O'ylayapman...")

    try:
        answer = await asyncio.to_thread(_generate, tg_id, question)
        await asyncio.to_thread(_finish, tg_id, question, answer)
        left = max(AI_DAILY_LIMIT - (used + 1), 0)
        await msg.edit_text(
            f"{answer}\n\n"
            f"<i>💬 Limit: {left}/{AI_DAILY_LIMIT}</i>"
        )
    except Exception:
        log.exception("AI xato")
        await msg.edit_text(
            "❌ AI hozir javob bera olmadi. Birozdan keyin qayta urinib ko'ring."
        )


@router.callback_query(F.data == "ai:stop")
async def ai_stop_cb(callback, state: FSMContext):
    await state.clear()
    await callback.message.answer("✅ AI sessiyasi tugadi.")
    await callback.answer()