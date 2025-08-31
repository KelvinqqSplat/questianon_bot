from aiogram import Router, F
import re
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, FSInputFile
import os
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest

from ..config import ADMIN_IDS
from ..db import (
    list_users, get_user_profile, global_stats, add_global_ban, remove_global_ban,
    is_globally_banned, recent_reports, export_users_csv, search_users
)
from ..keyboards.admin import admin_menu, users_pager, user_actions, reports_list_kb, back_to_admin

router = Router()

async def _safe_edit(message, text=None, reply_markup=None, parse_mode=None):
    try:
        if text is None:
            text = message.html_text if hasattr(message, 'html_text') else message.text
        await message.edit_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
    except TelegramBadRequest as e:
        if 'message is not modified' in str(e):
            try:
                await message.edit_reply_markup(reply_markup=reply_markup)
            except TelegramBadRequest:
                pass
        else:
            raise

@router.message(Command("admin"))
async def admin_entry(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    await message.answer("<b>Админ-панель</b>", parse_mode=ParseMode.HTML, reply_markup=admin_menu())

@router.callback_query(F.data == "admin:menu")
async def cb_menu(call: CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        await call.answer()
        return
    await _safe_edit(call.message, "<b>Админ-панель</b>", parse_mode=ParseMode.HTML, reply_markup=admin_menu())
    await call.answer()

# ---- Users ----
@router.callback_query(F.data.regexp(r"^admin:users:(\d+)$"))
async def cb_users(call: CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        await call.answer()
        return
    parts = call.data.split(':')
    m = parts[-1]
    page = int(m)
    limit = 10
    offset = page * limit
    rows = await list_users(limit=limit, offset=offset)
    if not rows and page > 0:
        page = max(page-1, 0)
        offset = page * limit
        rows = await list_users(limit=limit, offset=offset)
    lines = ["<b>Пользователи</b>"]
    for r in rows:
        uid, username, fn, ln, is_admin, created = r
        tag = f"@{username}" if username else "—"
        lines.append(f"• <code>{uid}</code> {tag} — {fn or ''} {ln or ''}")
    text = "\n".join(lines) or "Пока пусто"
    await _safe_edit(call.message, text, parse_mode=ParseMode.HTML, reply_markup=users_pager(page))
    await call.answer()

@router.callback_query(F.data.regexp(r"^admin:user:(\d+)$"))
async def cb_user(call: CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        await call.answer()
        return
    uid = int(call.data.split(':')[2])
    user, total, pending, answered = await get_user_profile(uid)
    if not user:
        await call.answer("Пользователь не найден", show_alert=True)
        return
    banned = await is_globally_banned(uid)
    u_id, username, fn, ln, is_admin, created = user
    text = (
        "<b>Профиль пользователя</b>\n"
        f"ID: <code>{u_id}</code>\n"
        f"Username: @{username or '—'}\n"
        f"Имя: {fn or ''} {ln or ''}\n"
        f"Админ: {'да' if is_admin else 'нет'}\n"
        f"Создан: {created}\n"
        f"Всего вопросов: <b>{total}</b> | Ожидают: <b>{pending}</b> | Отвечено: <b>{answered}</b>\n"
        f"Бан: {'да' if banned else 'нет'}"
    )
    await _safe_edit(call.message, text, parse_mode=ParseMode.HTML, reply_markup=user_actions(uid, banned))
    await call.answer()

@router.callback_query(F.data.regexp(r"^admin:ban:(\d+)$"))
async def cb_ban(call: CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        await call.answer()
        return
    uid = int(call.data.split(':')[2])
    await add_global_ban(uid)
    await cb_user(call)

@router.callback_query(F.data.regexp(r"^admin:unban:(\d+)$"))
async def cb_unban(call: CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        await call.answer()
        return
    uid = int(call.data.split(':')[2])
    await remove_global_ban(uid)
    await cb_user(call)

# ---- Reports ----
@router.callback_query(F.data.regexp(r"^admin:reports:(\d+)$"))
async def cb_reports(call: CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        await call.answer()
        return
    parts = call.data.split(':')
    m = parts[-1]
    page = int(m)
    limit = 10
    offset = page * limit
    rows = await recent_reports(limit=limit, offset=offset)
    lines = ["<b>Жалобы</b>"]
    for r in rows:
        rep_id, reporter_id, thread_id, created_at, target_user_id, asker_id, question_text, reply_text = r
        lines.append(
            f"#{rep_id} • thread {thread_id} • reporter <code>{reporter_id}</code> • "
            f"target <code>{target_user_id}</code> • asker <code>{asker_id}</code>\n"
            f"Q: {question_text[:80]}{'…' if len(question_text)>80 else ''}"
        )
        if reply_text:
            lines.append(f"A: {reply_text[:80]}{'…' if len(reply_text)>80 else ''}")
        lines.append("")

    text = "\n".join(lines) or "Жалоб нет"
    await _safe_edit(call.message, text, parse_mode=ParseMode.HTML, reply_markup=reports_pager(page))
    await call.answer()

# ---- Logs ----
@router.callback_query(F.data == "admin:search")
async def cb_search(call: CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        await call.answer(); return
    await _safe_edit(call.message, "Отправь строку поиска: username, имя или ID.")
    # Mark pending search using a simple convention in bot memory via message reply (no persistent FSM)
    # We'll rely on a special prefix in the next message: 'ADMIN_SEARCH: <query>'
    await call.message.answer("Напиши: <code>ADMIN_SEARCH: &lt;запрос&gt;</code>", parse_mode=ParseMode.HTML)
    await call.answer()

@router.callback_query(F.data == "admin:logs")
async def cb_logs(call: CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        await call.answer()
        return
    try:
        with open("logs/app.log", "r", encoding="utf-8") as f:
            tail = f.readlines()[-120:]  # последние ~120 строк
        content = "".join(tail)
        if len(content) > 3500:
            content = content[-3500:]
        text = "<b>Последние строки лога</b>\n<pre>" + (content.replace("<","&lt;").replace(">","&gt;")) + "</pre>"
        from ..keyboards.admin import admin_menu
        await _safe_edit(call.message, text, parse_mode=ParseMode.HTML, reply_markup=admin_menu())
    except FileNotFoundError:
        await _safe_edit(call.message, "Лог-файл пока пуст. Действий ещё не было.", reply_markup=admin_menu())
    await call.answer()

# ---- Export ----
@router.callback_query(F.data == "admin:export_users")
async def cb_export_users(call: CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        await call.answer()
        return
    path = "users_export.csv"
    await export_users_csv(path)
    await call.message.answer_document(FSInputFile(path), caption="Экспорт пользователей")
    await call.answer()


@router.callback_query(F.data == "admin:logs:clear")
async def cb_logs_clear(call: CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        await call.answer(); return
    try:
        os.makedirs("logs", exist_ok=True)
        open("logs/app.log", "w", encoding="utf-8").close()
        await call.message.answer("Лог очищен.")
    except Exception as e:
        await call.message.answer(f"Не удалось очистить лог: {e}")
    await call.answer()


from ..db import fetch_threads_for_user, export_threads_csv
from ..keyboards.admin import threads_filter_menu

@router.callback_query(F.data.regexp(r"^admin:threads:(\d+):(all|pending|answered):(\d+)$"))
async def cb_threads(call: CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        await call.answer(); return
    parts = call.data.split(':')
    uid = int(parts[2]); status = parts[3]; days = int(parts[4])
    rows = await fetch_threads_for_user(uid, status=status, days=days, limit=15, offset=0)
    if not rows:
        text = "<b>Треды</b> — ничего не найдено по фильтру."
    else:
        lines = [f"<b>Треды пользователя</b> <code>{uid}</code> — {status}, {days}д"]
        for (tid, asker_id, q, a, created_at, replied_at) in rows:
            line = f"#{tid} • asker <code>{asker_id}</code> • {created_at}\nQ: {q[:120]}{'…' if len(q)>120 else ''}"
            if a:
                line += f"\nA: {a[:120]}{'…' if len(a)>120 else ''}"
            lines.append(line)
        text = "\n\n".join(lines)
    await _safe_edit(call.message, text, parse_mode=ParseMode.HTML, reply_markup=threads_filter_menu(uid))
    await call.answer()

@router.callback_query(F.data.regexp(r"^admin:threads_export:(\d+):(all|pending|answered):(\d+)$"))
async def cb_threads_export(call: CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        await call.answer(); return
    parts = call.data.split(':')
    uid = int(parts[2]); status = parts[3]; days = int(parts[4])
    path = f"threads_{uid}_{status}_{days}d.csv"
    await export_threads_csv(uid, status=status, days=days, path=path)
    await call.message.answer_document(FSInputFile(path), caption=f"Экспорт тредов: user {uid}, {status}, {days}д")
    await call.answer()


@router.callback_query(F.data == "admin:nop")
async def cb_nop(call: CallbackQuery):
    await call.answer()


@router.message(F.text.startswith("ADMIN_SEARCH:"))
async def msg_admin_search_prefix(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    q = message.text.split(":", 1)[1].strip()
    if not q:
        await message.answer("Пустой запрос. Пример: <code>ADMIN_SEARCH: username</code>", parse_mode=ParseMode.HTML)
        return
    rows = await search_users(q, limit=20, offset=0)
    if not rows:
        await message.answer("Ничего не найдено.")
        return
    lines = ["<b>Результаты поиска</b>"]
    for r in rows:
        uid, username, fn, ln, is_admin, created = r
        tag = f"@{username}" if username else "—"
        lines.append(f"• <code>{uid}</code> {tag} — {fn or ''} {ln or ''}")
    lines.append("\nОткрой меню /admin → Пользователи и листай до нужного ID.")
    await message.answer("\n".join(lines), parse_mode=ParseMode.HTML)


@router.callback_query(F.data == "admin:stats")
async def cb_stats(call: CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        await call.answer(); return
    users, threads, reports = await global_stats()
    from ..keyboards.admin import back_to_admin
    text = ("<b>Статистика</b>\n"
            f"Пользователей: <b>{users}</b>\n"
            f"Вопросов: <b>{threads}</b>\n"
            f"Жалоб: <b>{reports}</b>")
    await _safe_edit(call.message, text, parse_mode=ParseMode.HTML, reply_markup=back_to_admin())
    await call.answer()


@router.callback_query(F.data.regexp(r"^admin:reports2:(\d+)$"))
async def cb_reports2(call: CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        await call.answer(); return
    page = int(call.data.split(':')[2])
    limit = 10; offset = page * limit
    rows = await recent_reports(limit=limit, offset=offset)
    report_ids = [r[0] for r in rows] if rows else []
    from ..keyboards.admin import reports_list_kb
    lines = ["<b>Жалобы</b>"] + ([ "Пока пусто." ] if not rows else [
        f"#{rep_id} • thread <code>{thread_id}</code> • reporter <code>{reporter_id}</code> • {created_at}"
        for (rep_id, reporter_id, thread_id, created_at, target_user_id, asker_id, q, a) in rows
    ])
    await _safe_edit(call.message, "\n".join(lines), parse_mode=ParseMode.HTML, reply_markup=reports_list_kb(report_ids, page))
    await call.answer()


@router.callback_query(F.data.regexp(r"^admin:report:(\d+)$"))
async def cb_report_details(call: CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        await call.answer(); return
    rid = int(call.data.split(':')[2])
    from ..db import db_conn
    async with db_conn() as conn:
        async with conn.execute(
            "SELECT r.id, r.reporter_id, r.thread_id, r.created_at, t.target_user_id, t.asker_id, t.question_text, t.reply_text "
            "FROM reports r JOIN threads t ON t.id = r.thread_id WHERE r.id=?", (rid,)
        ) as cur:
            r = await cur.fetchone()
    if not r:
        await call.answer("Жалоба не найдена", show_alert=True); return
    rep_id, reporter_id, thread_id, created_at, target_user_id, asker_id, q, a = r
    from ..keyboards.admin import back_to_admin
    text = (f"<b>Жалоба #{rep_id}</b>\n"
            f"Thread: <code>{thread_id}</code>\n"
            f"Reporter: <code>{reporter_id}</code>\n"
            f"Target user: <code>{target_user_id}</code>\n"
            f"Asker: <code>{asker_id}</code>\n"
            f"Создана: {created_at}\n\n"
            f"<b>Вопрос</b>:\n{(q or '—')}\n\n"
            f"<b>Ответ</b>:\n{(a or '—')}")
    await _safe_edit(call.message, text, parse_mode=ParseMode.HTML, reply_markup=back_to_admin())
    await call.answer()


@router.callback_query(F.data.regexp(r"^admin:gthreads:(all|pending|answered):(\d+):(\d+)$"))
async def cb_gthreads(call: CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        await call.answer(); return
    from ..db import fetch_threads_global
    parts = call.data.split(':')
    status = parts[2]; days = int(parts[3]); page = int(parts[4])
    limit = 10; offset = page * limit
    rows = await fetch_threads_global(status=status, days=days, limit=limit, offset=offset)
    if not rows:
        text = f"<b>Все треды</b> — ничего не найдено ({status}, {days}д)."
    else:
        lines = [f"<b>Все треды</b> — {status}, {days}д"]
        for (tid, target_user_id, asker_id, q, a, created_at, replied_at) in rows:
            line = f"#{tid} • to <code>{target_user_id}</code> • from <code>{asker_id}</code> • {created_at}\nQ: { (q or '')[:140] }"
            if a:
                line += f"\nA: {a[:140]}"
            lines.append(line)
        text = "\n\n".join(lines)
    from ..keyboards.admin import threads_global_pager
    await _safe_edit(call.message, text, parse_mode=ParseMode.HTML, reply_markup=threads_global_pager(status, days, page))
    await call.answer()