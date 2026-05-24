from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardRemove,
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

def share_phone_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Поділитися номером", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

def experience_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Так, є досвід", callback_data="exp:yes")],
        [InlineKeyboardButton(text="❌ Ні, досвіду немає", callback_data="exp:no")],
    ])

def remove_kb() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()
