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
