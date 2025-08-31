import re
from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery

from ..config import ADMIN_IDS
from ..db import get_asker_by_thread, set_pending_reply, block_user, add_report
from ..keyboards.common import main_menu, back_to_user, back_to_user

router = Router()

async def _safe_edit(message, text=None, reply_markup=None, parse_mode=None):
    try:
        if text is None:
            text = message.html_text if hasattr(message, 'html_text') else message.text
        await message.edit_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
    except TelegramBadRequest as e:
        if 'message is not modified' in str(e).lower():
            try:
                await message.edit_reply_markup(reply_markup=reply_markup)
            except TelegramBadRequest:
                pass
        else:
            raise

@router.callback_query(F.data == "profile")
async def cb_profile(call: CallbackQuery):
    u = call.from_user
    await _safe_edit(call.message, 
        "<b>Профиль</b>\n"
        f"ID: <code>{u.id}</code>\n"
        f"Имя: {u.full_name}\n"
        f"Username: @{u.username if u.username else '—'}",
        reply_markup=back_to_user(),
        parse_mode="HTML",
    )
    await call.answer()

@router.callback_query(F.data == "my_link")
async def cb_my_link(call: CallbackQuery):
    from ..services.links import ensure_user_token, build_deeplink
    token = await ensure_user_token(call.from_user.id)
    link = await build_deeplink(call.bot, token)
    await _safe_edit(call.message, 
        f"Твоя ссылка:\n<code>{link}</code>",
        reply_markup=back_to_user(),
        parse_mode="HTML",
    )
    await call.answer()

@router.callback_query(F.data == "help")
async def cb_help(call: CallbackQuery):
    await _safe_edit(call.message, 
        "Этот бот принимает анонимные вопросы по персональной ссылке и позволяет отвечать на них.",
        reply_markup=back_to_user(),
    )
    await call.answer()

@router.callback_query(F.data.regexp(r"^reply:(\d+)$"))
async def cb_reply(call: CallbackQuery):
    m = re.fullmatch(r"reply:(\d+)", call.data)
    thread_id = int(m.group(1))
    await set_pending_reply(call.from_user.id, thread_id)
    await call.message.answer("Напиши ответ на этот вопрос одним сообщением. /cancel — отменить.")
    await call.answer()

@router.callback_query(F.data.regexp(r"^block:(\d+)$"))
async def cb_block(call: CallbackQuery):
    m = re.fullmatch(r"block:(\d+)", call.data)
    thread_id = int(m.group(1))
    from ..db import get_asker_by_thread
    asker_id = await get_asker_by_thread(thread_id)
    if not asker_id:
        await call.answer("Не удалось найти отправителя.", show_alert=True)
        return
    await block_user(call.from_user.id, asker_id)
    await call.answer("Отправитель заблокирован для вас.", show_alert=True)

@router.callback_query(F.data.regexp(r"^report:(\d+)$"))
async def cb_report(call: CallbackQuery):
    m = re.fullmatch(r"report:(\d+)", call.data)
    thread_id = int(m.group(1))
    await add_report(call.from_user.id, thread_id)
    # notify admins silently
    from ..config import ADMIN_IDS
    for aid in ADMIN_IDS:
        try:
            await call.bot.send_message(aid, f"⚠️ Жалоба на тред #{thread_id} от @{call.from_user.username or call.from_user.id}")
        except Exception:
            pass
    await call.answer("Жалоба отправлена администраторам.", show_alert=True)


@router.callback_query(F.data == "user:menu")
async def cb_user_menu(call: CallbackQuery):
    from aiogram.exceptions import TelegramBadRequest
    from ..keyboards.common import main_menu
    # Try to keep current text and only swap keyboard to main menu
    try:
        await call.message.edit_reply_markup(reply_markup=main_menu())
    except TelegramBadRequest:
        # Fallback: redraw fully
        await _safe_edit(
            call.message,
            "<b>Этот бот принимает анонимные вопросы по персональной ссылке и позволяет отвечать на них.</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu()
        )
    await call.answer()
