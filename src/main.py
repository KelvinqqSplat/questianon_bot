import os
import logging
import threading
import asyncio
from fastapi import FastAPI
import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message
from aiogram.filters import Command

from .config import BOT_TOKEN
from .middlewares.rate_limit import RateLimitMiddleware

# Импортируем все роутеры
from .handlers.start import router as start_router
from .handlers.commands import router as commands_router
from .handlers.callbacks import router as callbacks_router
from .handlers.inline import router as inline_router
from .handlers.text import router as text_router
from .handlers.admin import router as admin_router

# Создаём бота и диспетчер
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# ========== СОБСТВЕННЫЙ BROADCAST ==========
# Читаем SUPER_ADMIN_IDS из переменных окружения
SUPER_ADMIN_IDS = []
if os.getenv("SUPER_ADMIN_IDS"):
    SUPER_ADMIN_IDS = list(map(int, os.getenv("SUPER_ADMIN_IDS").split(",")))

@dp.message(Command("broadcast"))
async def broadcast_cmd(message: Message):
    # Проверка прав
    if message.from_user.id not in SUPER_ADMIN_IDS:
        await message.reply("⛔ У вас нет прав на рассылку.")
        return

    text = message.text.replace("/broadcast", "").strip()
    if not text:
        await message.reply("📝 Напишите текст рассылки после команды.\nПример: /broadcast Привет всем!")
        return

    confirm = await message.reply("📨 Начинаю рассылку...")

    # Получаем всех пользователей из БД
    from .database import db_conn
    async with db_conn() as conn:
        async with conn.execute("SELECT user_id FROM users") as cur:
            users = await cur.fetchall()

    if not users:
        await confirm.edit_text("❌ Нет пользователей для рассылки.")
        return

    count = 0
    for (user_id,) in users:
        try:
            await bot.send_message(user_id, text)
            count += 1
            await asyncio.sleep(0.05)
        except Exception:
            pass

    await confirm.edit_text(f"✅ Рассылка завершена. Отправлено {count} из {len(users)} пользователей.")
# ===========================================

# Подключаем middlewares
dp.message.middleware(RateLimitMiddleware())
dp.callback_query.middleware(RateLimitMiddleware())

# Подключаем роутеры (порядок важен)
dp.include_router(start_router)
dp.include_router(admin_router)
dp.include_router(commands_router)
dp.include_router(callbacks_router)
dp.include_router(inline_router)
dp.include_router(text_router)

# FastAPI для keep-alive
app = FastAPI()

@app.get("/")
def health():
    return {"status": "ok"}

def run_webserver():
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

async def main():
    logging.info("Starting bot polling...")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    threading.Thread(target=run_webserver, daemon=True).start()
    asyncio.run(main())
