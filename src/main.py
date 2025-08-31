# FastAPI webhook entry for Koyeb
import os
import logging
from fastapi import FastAPI, Request, Response
from aiogram import Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.bot import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.types import Update as TgUpdate
from aiogram import Bot

from .config import BOT_TOKEN
from .middlewares.rate_limit import RateLimitMiddleware

# Read env
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "supersecret")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL")  # e.g. https://your-app-name.koyeb.app

app = FastAPI()
dp: Dispatcher | None = None
bot: Bot | None = None

@app.on_event("startup")
async def on_startup():
    global dp, bot
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    # Create bot and dispatcher
    session = AiohttpSession()
    bot = Bot(BOT_TOKEN, session=session, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    # Middlewares
    dp.message.middleware(RateLimitMiddleware())
    dp.callback_query.middleware(RateLimitMiddleware())

    # Routers
    from .handlers.start import router as start_router
    from .handlers.commands import router as commands_router
    from .handlers.callbacks import router as callbacks_router
    from .handlers.inline import router as inline_router
    from .handlers.text import router as text_router
    from .handlers.admin import router as admin_router

    # Important: admin first, then others
    dp.include_router(start_router)
    dp.include_router(admin_router)
    dp.include_router(commands_router)
    dp.include_router(callbacks_router)
    dp.include_router(inline_router)
    dp.include_router(text_router)

    # Set webhook
    if not PUBLIC_BASE_URL:
        raise RuntimeError("PUBLIC_BASE_URL env is required for webhook mode")
    webhook_url = f"{PUBLIC_BASE_URL}/webhook/{WEBHOOK_SECRET}"
    await bot.set_webhook(webhook_url)
    logging.info(f"Webhook set to %s", webhook_url)

@app.on_event("shutdown")
async def on_shutdown():
    if bot:
        await bot.session.close()

@app.get("/")
async def health():
    return {"ok": True}

@app.post("/webhook/{secret}")
async def telegram_webhook(secret: str, request: Request):
    if secret != WEBHOOK_SECRET:
        return Response(status_code=403)
    body = await request.json()
    update = TgUpdate.model_validate(body)
    await dp.feed_update(bot, update)
    return Response(status_code=200)
