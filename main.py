import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from database.db import init_db
from handlers import user_menu, deposit, withdraw, promo, admin, chat

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")


async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    await init_db()

    # الترتيب مهم جداً:
    # 1. user_menu أول عشان /start يشتغل فوراً
    # 2. admin, deposit, withdraw, promo للستيتس والأزرار الثابتة
    # 3. chat آخر حاجة للأزرار الديناميكية
    dp.include_router(user_menu.router)
    dp.include_router(admin.router)
    dp.include_router(deposit.router)
    dp.include_router(withdraw.router)
    dp.include_router(promo.router)
    dp.include_router(chat.router)

    print("✅ البوت شغال...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
