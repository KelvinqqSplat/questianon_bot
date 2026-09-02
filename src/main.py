import os
import logging
import threading
from fastapi import FastAPI
import uvicorn
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command

# Твой токен
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set")

# Создаём бота и диспетчер
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# Обработчик команды /start (простой пример)
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer("Привет! Бот работает через polling.")

# Если у тебя есть другие хендлеры – импортируй их сюда
# from .handlers import router
# dp.include_router(router)

# Функция запуска бота в отдельном потоке
def run_bot():
    logging.info("Starting bot polling...")
    dp.run_polling(bot, skip_updates=True)

# FastAPI для keep-alive
app = FastAPI()

@app.get("/")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Запускаем бота в фоновом потоке
    threading.Thread(target=run_bot, daemon=True).start()
    # Запускаем веб-сервер на порту от Render
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
