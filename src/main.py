import os
import logging
import threading
import asyncio
from fastapi import FastAPI
import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from .config import BOT_TOKEN
from .middlewares.rate_limit import RateLimitMiddleware

# Импортируем все роутеры из папки handlers
from .handlers.start import router as start_router
from .handlers.commands import router as commands_router
from .handlers.callbacks import router as callbacks_router
from .handlers.inline import router as inline_router
from .handlers.text import router as text_router
from .handlers.admin import router as admin_router

# === Собственный broadcast ===
from aiogram.types import Message
from aiogram.filters import Command
import os

# Суперадмины из переменной окружения
SUPER_ADMIN_IDS = list(map(int, os.getenv("SUPER_ADMIN_IDS", "").split(","))) if os.getenv("SUPER_ADMIN_IDS") else []

@dp.message(Command("broadcast"))
async def broadcast_cmd(message: Message):
    # Проверяем права
    if message.from_user.id not in SUPER_ADMIN_IDS:
        await message.reply("⛔ У вас нет прав на рассылку.")
        return
    
    # Получаем текст после команды
    text = message.text.replace("/broadcast", "").strip()
    if not text:
        await message.reply("📝 Напишите текст рассылки после команды.\nПример: /broadcast Привет всем!")
        return
    
    # Подтверждение
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
            await asyncio.sleep(0.05)  # защита от флуда
        except Exception:
            pass  # игнорируем тех, кто заблокировал бота
    
    await confirm.edit_text(f"✅ Рассылка завершена. Отправлено {count} из {len(users)} пользователей.")

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# Подключаем middlewares
dp.message.middleware(RateLimitMiddleware())
dp.callback_query.middleware(RateLimitMiddleware())

# Подключаем все роутеры (порядок важен)
dp.include_router(start_router)
dp.include_router(admin_router)
dp.include_router(commands_router)
dp.include_router(callbacks_router)
dp.include_router(inline_router)
dp.include_router(text_router)

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
    # Запускаем веб-сервер в фоновом потоке
    threading.Thread(target=run_webserver, daemon=True).start()
    # Запускаем бота в главном потоке
    asyncio.run(main())
