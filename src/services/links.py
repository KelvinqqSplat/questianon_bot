import secrets
from aiogram import Bot

from ..db import fetch_token, get_or_create_token

_cached_username = None

async def bot_username(bot: Bot) -> str:
    global _cached_username
    if not _cached_username:
        me = await bot.get_me()
        _cached_username = me.username
    return _cached_username

def new_token() -> str:
    return secrets.token_urlsafe(8).rstrip("=")

async def ensure_user_token(user_id: int) -> str:
    token = await fetch_token(user_id)
    if token:
        return token
    token = new_token()
    await get_or_create_token(user_id, token)
    return token

async def build_deeplink(bot: Bot, token: str) -> str:
    username = await bot_username(bot)
    return f"https://t.me/{username}?start=ask_{token}"
