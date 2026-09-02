import os
import logging
import threading
import asyncio
from fastapi import FastAPI
import uvicorn
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set")

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer("Привет! Бот работает через polling.")

# Если есть другие хендлеры – подключи их (раскомментируй)
# from .handlers import router
# dp.include_router(router)

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
    # Запускаем бота в главном потоке (чтобы сигналы работали)
    asyncio.run(main())
