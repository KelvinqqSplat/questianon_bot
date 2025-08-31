from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def admin_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Пользователи", callback_data="admin:users:0"), InlineKeyboardButton(text="🔎 Поиск", callback_data="admin:search")],
        [InlineKeyboardButton(text="🗂 Жалобы", callback_data="admin:reports2:0"), InlineKeyboardButton(text="📬 Все треды", callback_data="admin:gthreads:all:30:0")],
        [InlineKeyboardButton(text="📈 Статистика", callback_data="admin:stats")],
        [InlineKeyboardButton(text="🧾 Логи", callback_data="admin:logs"), InlineKeyboardButton(text="🧹 Очистить", callback_data="admin:logs:clear")],
        [InlineKeyboardButton(text="📤 Экспорт users.csv", callback_data="admin:export_users")],
    ])

def users_pager(page: int):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="⟨", callback_data=f"admin:users:{max(page-1,0)}"),
        InlineKeyboardButton(text=f"Стр. {page+1}", callback_data="admin:nop"),
        InlineKeyboardButton(text="⟩", callback_data=f"admin:users:{page+1}"),
    ], [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:menu")]])

def user_actions(user_id: int, banned: bool):
    rows = [
        [InlineKeyboardButton(text="📬 Треды", callback_data=f"admin:threads:{user_id}:all:30")],
        [InlineKeyboardButton(text=("✅ Разбанить" if banned else "⛔️ Забанить"), callback_data=f"admin:{'unban' if banned else 'ban'}:{user_id}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:users:0")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)

def threads_filter_menu(user_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Все • 7д", callback_data=f"admin:threads:{user_id}:all:7"),
         InlineKeyboardButton(text="Все • 30д", callback_data=f"admin:threads:{user_id}:all:30"),
         InlineKeyboardButton(text="Все • 90д", callback_data=f"admin:threads:{user_id}:all:90")],
        [InlineKeyboardButton(text="Ожидают • 30д", callback_data=f"admin:threads:{user_id}:pending:30"),
         InlineKeyboardButton(text="Отвеченные • 30д", callback_data=f"admin:threads:{user_id}:answered:30")],
        [InlineKeyboardButton(text="📤 Экспорт CSV", callback_data=f"admin:threads_export:{user_id}:all:90")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:users:0")],
    ])

def back_to_admin():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:menu")]])

def reports_list_kb(report_ids, page: int):
    rows = []
    for rid in report_ids:
        rows.append([InlineKeyboardButton(text=f"Подробнее #{rid}", callback_data=f"admin:report:{rid}")])
    rows.append([
        InlineKeyboardButton(text="⟨", callback_data=f"admin:reports2:{max(page-1,0)}"),
        InlineKeyboardButton(text=f"Стр. {page+1}", callback_data="admin:nop"),
        InlineKeyboardButton(text="⟩", callback_data=f"admin:reports2:{page+1}"),
    ])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def threads_global_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Все • 30д", callback_data="admin:gthreads:all:30:0")],
        [InlineKeyboardButton(text="Ожидают • 30д", callback_data="admin:gthreads:pending:30:0")],
        [InlineKeyboardButton(text="Отвеченные • 30д", callback_data="admin:gthreads:answered:30:0")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:menu")],
    ])

def threads_global_pager(status: str, days: int, page: int):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="⟨", callback_data=f"admin:gthreads:{status}:{days}:{max(page-1,0)}"),
        InlineKeyboardButton(text=f"Стр. {page+1}", callback_data="admin:nop"),
        InlineKeyboardButton(text="⟩", callback_data=f"admin:gthreads:{status}:{days}:{page+1}"),
    ], [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:menu")]])
