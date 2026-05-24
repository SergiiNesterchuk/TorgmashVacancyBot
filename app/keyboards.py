from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)

def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📝 Подати заявку")]],
        resize_keyboard=True,
    )

def yes_no_kb(prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Так", callback_data=f"{prefix}:yes"),
        InlineKeyboardButton(text="❌ Ні", callback_data=f"{prefix}:no"),
    ]])

def confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Підтвердити", callback_data="confirm:yes"),
        InlineKeyboardButton(text="🔄 Заповнити знову", callback_data="confirm:restart"),
    ]])
