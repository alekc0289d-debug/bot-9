"""Maktab Telegram Bot — aiogram v3.

Ishga tushirish:  python run_bot.py
(Avval fayl nomi bot.py edi va bot/ paketi bilan to'qnashardi.)
"""

import asyncio

from bot.instance import bot, dp, log
from bot.commands import setup_commands
from bot.handlers import start, menu, admin, group, ai, student, parent, teacher
from bot.scheduler import daily, daily_grades, weekly, monthly
from bot.utils.lang_mw import LangMiddleware

dp.update.outer_middleware(LangMiddleware())

dp.include_router(start.router)
dp.include_router(menu.router)
dp.include_router(admin.router)
dp.include_router(student.router)
dp.include_router(parent.router)
dp.include_router(teacher.router)
dp.include_router(ai.router)
dp.include_router(group.router)


async def main():
    log.info("🚀 Bot ishga tushmoqda...")

    await bot.delete_webhook(drop_pending_updates=True)

    me = await bot.get_me()
    log.info("✅ Bot: @%s (%s)", me.username, me.full_name)

    await setup_commands(bot)

    daily.start()
    daily_grades.start()
    weekly.start()
    monthly.start()

    try:
        await dp.start_polling(bot)
    finally:
        for mod in (daily, daily_grades, weekly, monthly):
            try:
                mod.stop()
            except Exception:
                pass
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        log.info("🛑 Bot to'xtatildi")
