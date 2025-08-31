from aiogram import Router, F
from aiogram.types import Message

from ..config import ADMIN_IDS
from ..db import (
    upsert_user, pop_pending_reply, get_asker_by_thread, save_reply,
    pop_pending_question, create_thread, is_blocked
)
from ..keyboards.common import thread_actions

router = Router()

@router.message(F.text)
async def text_router(message: Message):
    await upsert_user(message, ADMIN_IDS)

    # Глобальный бан
    from ..db import is_globally_banned
    if await is_globally_banned(message.from_user.id):
        await message.answer("Доступ ограничен администраторами.")
        return

    # 1) Ответ на анонимный вопрос
    from ..db import pop_pending_reply
    pending_thread_id = await pop_pending_reply(message.from_user.id)
    if pending_thread_id:
        asker_id = await get_asker_by_thread(pending_thread_id)
        if not asker_id:
            await message.answer("Не удалось найти тему для ответа (возможно, устарела).")
            return
        await save_reply(pending_thread_id, message.text)
        try:
            await message.bot.send_message(
                asker_id,
                "<b>Ответ на твой анонимный вопрос</b>:\n\n" + message.text,
                parse_mode="HTML",
            )
        except Exception:
            pass
        await message.answer("Ответ отправлен анониму ✅")
        return

    # 2) Приём анонимного вопроса по deeplink
    target_user_id = await pop_pending_question(message.from_user.id)
    if target_user_id:
        # check blocklist
        if await is_blocked(target_user_id, message.from_user.id):
            await message.answer("Получатель запретил получение сообщений от тебя.")
            return
        thread_id = await create_thread(target_user_id, message.from_user.id, message.text)
        try:
            await message.bot.send_message(
                target_user_id,
                "<b>Новый анонимный вопрос</b>:\n\n" + message.text,
                reply_markup=thread_actions(thread_id),
                parse_mode="HTML",
            )
        except Exception:
            pass
        await message.answer("Вопрос отправлен анонимно ✅")
        return

    # 3) Иначе: подсказка
    await message.answer("Я принимаю и передаю анонимные вопросы. Нажми /link, чтобы получить персональную ссылку.")






async def _reject_other_media(message: Message):
    await message.answer("Этот тип медиа не поддерживается. Разрешены: текст, стикеры и голосовые.")

