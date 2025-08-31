from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from ..config import ADMIN_IDS
from ..db import upsert_user, stats_for_user, global_stats,     pop_pending_question, pop_pending_reply
from ..services.links import ensure_user_token, build_deeplink

router = Router()

@router.message(Command("link"))
async def cmd_link(message: Message):
    await upsert_user(message, ADMIN_IDS)
    token = await ensure_user_token(message.from_user.id)
    link = await build_deeplink(message.bot, token)
    await message.answer(
        "Твоя персональная ссылка для анонимных вопросов:\n"
        f"<code>{link}</code>\n\n"
        "Поделись ей в соцсетях.",
        parse_mode="HTML",
    )

@router.message(Command("cancel"))
async def cmd_cancel(message: Message):
    await pop_pending_question(message.from_user.id)
    await pop_pending_reply(message.from_user.id)
    await message.answer("Действие отменено.")

@router.message(Command("stats"))
async def cmd_stats(message: Message):
    total, pending, answered = await stats_for_user(message.from_user.id)
    await message.answer(
        "<b>Статистика</b>\n"
        f"Всего вопросов: <b>{total}</b>\n"
        f"Ожидают ответа: <b>{pending}</b>\n"
        f"Отвечено: <b>{answered}</b>",
        parse_mode="HTML",
    )

@router.message(Command("admin_stats"))
async def cmd_admin(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    users, threads, reports = await global_stats()
    await message.answer(
        "<b>Админ-панель</b>\n"
        f"Пользователей: <b>{users}</b>\n"
        f"Вопросов: <b>{threads}</b>\n"
        f"Жалоб: <b>{reports}</b>",
        parse_mode="HTML",
    )

@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("Команда доступна только администраторам.")
        return
    # everything after command is the text
    text = message.text.split(" ", 1)
    if len(text) < 2 or not text[1].strip():
        await message.answer("Использование: /broadcast <текст>")
        return
    payload = text[1].strip()

    # naive broadcast to all users
    from ..db import db_conn
    sent = 0
    async with db_conn() as conn:
        async with conn.execute("SELECT user_id FROM users") as cur:
            rows = await cur.fetchall()
            for (uid,) in rows:
                try:
                    await message.bot.send_message(uid, payload)
                    sent += 1
                except Exception:
                    pass
    await message.answer(f"Рассылка завершена. Отправлено: {sent}")
