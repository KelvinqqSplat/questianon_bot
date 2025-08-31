import re
from aiogram import Router, F
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from aiogram.enums import ParseMode

from ..config import ADMIN_IDS
from ..db import upsert_user, resolve_user_by_token, set_pending_question
from ..keyboards.common import main_menu

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message, command: CommandObject):
    await upsert_user(message, ADMIN_IDS)
    args = (command.args or "").strip()

    m = re.fullmatch(r"ask_([A-Za-z0-9_\-]+)", args or "")
    if m:
        token = m.group(1)
        target_user_id = await resolve_user_by_token(token)
        if not target_user_id:
            await message.answer("Ссылка недействительна или устарела. Попроси новую у адресата.")
            return
        await set_pending_question(message.from_user.id, target_user_id)
        await message.answer(
            "Отправь свой <b>анонимный вопрос</b> одним сообщением.\n\n"
            "Когда будешь готов — просто напиши его ниже. /cancel — отменить.",
            parse_mode=ParseMode.HTML,
        )
        return

    await message.answer(
        "<b>Привет!</b> Я бот для анонимных вопросов.\n\n"
        "Команды:\n"
        "• /link — получить персональную ссылку\n"
        "• /help — помощь\n"
        "• /stats — статистика\n"
        "• /cancel — отмена текущего шага",
        reply_markup=main_menu(),
        parse_mode=ParseMode.HTML,
    )

@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "<b>Как это работает</b>\n\n"
        "1) Нажми /link и получи персональную ссылку вида t.me/бот?start=ask_...\n"
        "2) Поделись ссылкой в соцсетях/сторис.\n"
        "3) Вопросы будут приходить тебе, отправитель останется анонимен.\n\n"
        "Ответ: под вопросом будет кнопка ✍️ Ответить — твой ответ уйдёт автору.",
        parse_mode=ParseMode.HTML,
    )
