from aiogram import Router
from aiogram.types import InlineQuery, InlineQueryResultArticle, InputTextMessageContent

from ..services.links import ensure_user_token, build_deeplink

router = Router()

@router.inline_query()
async def inline_share_link(query: InlineQuery):
    token = await ensure_user_token(query.from_user.id)
    link = await build_deeplink(query.bot, token)

    result = InlineQueryResultArticle(
        id=str(query.id),
        title="Поделиться ссылкой для анонимных вопросов",
        input_message_content=InputTextMessageContent(
            message_text=f"Задай мне вопрос анонимно: {link}"
        ),
        description="Вставит твою персональную ссылку",
    )
    await query.bot.answer_inline_query(query.id, results=[result], cache_time=1, is_personal=True)
