from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="👤 Профиль", callback_data="profile"),
                InlineKeyboardButton(text="🔗 Моя ссылка", callback_data="my_link"),
            ],
            [
                InlineKeyboardButton(text="ℹ️ Помощь", callback_data="help"),
            ],
        ]
    )

def thread_actions(thread_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✍️ Ответить", callback_data=f"reply:{thread_id}")],
            [
                InlineKeyboardButton(text="🚫 Заблокировать", callback_data=f"block:{thread_id}"),
                InlineKeyboardButton(text="⚠️ Жалоба", callback_data=f"report:{thread_id}"),
            ],
        ]
    )

def back_to_user():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="user:menu")]])
