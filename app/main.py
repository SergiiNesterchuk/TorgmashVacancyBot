import asyncio
import logging
import os
import time
import traceback
from html import escape as h

from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.fsm.context import FSMContext
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from .config import get_settings
from .states import Form
from .keyboards import main_menu_kb, yes_no_kb, confirm_kb

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

settings = get_settings()
bot = Bot(settings.bot_token)
dp = Dispatcher()

WEBHOOK_PATH = "/webhook"
TOTAL_STEPS = 5

VACANCY_TEXT = (
    "<b>Вакансія: Продавець-консультант</b> 💧\n\n"
    "📍 <b>Торгмаш</b>, вул. Онікієнка, 132 (Бровари)\n\n"
    "Продаж питної води та аксесуарів. Робота з клієнтами в магазині.\n\n"
    "❗️ <b>Дзвінки не потрібні</b> — заповни коротку анкету нижче, "
    "і ми зв'яжемося з тобою самі 🙂"
)


def _step(n: int) -> str:
    return f"<b>Крок {n}/{TOTAL_STEPS}</b>\n"


async def _clear_kb(c: CallbackQuery) -> None:
    try:
        await c.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass


# ==========================
#    /start
# ==========================
@dp.message(CommandStart())
async def start(m: Message, state: FSMContext):
    await state.clear()
    await m.answer(
        VACANCY_TEXT,
        parse_mode="HTML",
        reply_markup=main_menu_kb(),
    )


@dp.message(F.text == "📝 Подати заявку")
async def start_form(m: Message, state: FSMContext):
    await state.update_data(tg_username=m.from_user.username or "", tg_id=m.from_user.id)
    await m.answer(
        f"{_step(1)}Введи своє <b>ім'я</b>:",
        parse_mode="HTML",
    )
    await state.set_state(Form.first_name)


# ==========================
#    Анкета
# ==========================
@dp.message(Form.first_name)
async def get_first_name(m: Message, state: FSMContext):
    val = (m.text or "").strip()
    if len(val) < 2:
        return await m.answer("Будь ласка, введи ім'я (мінімум 2 символи).")
    await state.update_data(first_name=val)
    await m.answer(f"{_step(2)}Введи своє <b>прізвище</b>:", parse_mode="HTML")
    await state.set_state(Form.last_name)


@dp.message(Form.last_name)
async def get_last_name(m: Message, state: FSMContext):
    val = (m.text or "").strip()
    if len(val) < 2:
        return await m.answer("Будь ласка, введи прізвище (мінімум 2 символи).")
    await state.update_data(last_name=val)
    await m.answer(f"{_step(3)}Скільки тобі <b>років</b>?", parse_mode="HTML")
    await state.set_state(Form.age)


@dp.message(Form.age)
async def get_age(m: Message, state: FSMContext):
    txt = (m.text or "").strip()
    try:
        age = int(txt)
        if not (14 <= age <= 70):
            raise ValueError
    except ValueError:
        return await m.answer("Введи коректний вік (число від 14 до 70).")
    await state.update_data(age=age)
    await m.answer(
        f"{_step(4)}Ти проживаєш у <b>Броварах</b>?",
        reply_markup=yes_no_kb("brovary"),
        parse_mode="HTML",
    )
    await state.set_state(Form.brovary)


@dp.callback_query(Form.brovary, F.data.startswith("brovary:"))
async def get_brovary(c: CallbackQuery, state: FSMContext):
    await c.answer()
    await _clear_kb(c)
    ans = c.data.split(":", 1)[1]
    await state.update_data(brovary="Так" if ans == "yes" else "Ні")
    await c.message.answer(
        f"{_step(5)}Залиш свої <b>контактні дані</b>:\n\n"
        "• Номер телефону\n"
        "• або @username в Telegram\n"
        "• або посилання на соцмережу\n\n"
        "<i>Напиши будь-яким зручним способом</i>",
        parse_mode="HTML",
    )
    await state.set_state(Form.contact)


@dp.message(Form.contact)
async def get_contact(m: Message, state: FSMContext):
    val = (m.text or "").strip()
    if len(val) < 3:
        return await m.answer("Будь ласка, вкажи контактні дані.")
    await state.update_data(contact=val)

    data = await state.get_data()
    summary = _build_summary(data)
    await m.answer(
        f"<b>Перевір свої дані:</b>\n\n{summary}",
        reply_markup=confirm_kb(),
        parse_mode="HTML",
    )
    await state.set_state(Form.confirm)


def _build_summary(data: dict) -> str:
    lines = [
        f"• Ім'я: <b>{h(str(data.get('first_name', '')))}</b>",
        f"• Прізвище: <b>{h(str(data.get('last_name', '')))}</b>",
        f"• Вік: <b>{h(str(data.get('age', '')))}</b>",
        f"• Бровари: <b>{h(str(data.get('brovary', '—')))}</b>",
        f"• Контакт: <b>{h(str(data.get('contact', '')))}</b>",
    ]
    tg = data.get("tg_username", "")
    if tg:
        lines.append(f"• Telegram: @{h(tg)}")
    return "\n".join(lines)


@dp.callback_query(Form.confirm, F.data == "confirm:restart")
async def confirm_restart(c: CallbackQuery, state: FSMContext):
    await c.answer()
    await _clear_kb(c)
    await state.clear()
    await c.message.answer(
        VACANCY_TEXT,
        parse_mode="HTML",
        reply_markup=main_menu_kb(),
    )


@dp.callback_query(Form.confirm, F.data == "confirm:yes")
async def finalize(c: CallbackQuery, state: FSMContext):
    await c.answer()
    await _clear_kb(c)
    await c.message.answer("⏳ Відправляємо заявку…")

    data = await state.get_data()
    summary = _build_summary(data)

    group_msg = (
        "📋 <b>Нова заявка — Продавець Торгмаш</b>\n\n"
        f"{summary}"
    )

    try:
        await bot.send_message(
            settings.candidates_group_id,
            group_msg,
            parse_mode="HTML",
        )
        sent_ok = True
    except Exception as e:
        log.error("Failed to send to group: %s", e)
        sent_ok = False

    if sent_ok:
        await c.message.answer(
            "✅ <b>Заявку надіслано!</b>\n\n"
            "Ми розглянемо її та зв'яжемося з тобою найближчим часом.\n\n"
            "Дякуємо за інтерес до роботи в нашій команді 💧",
            parse_mode="HTML",
            reply_markup=main_menu_kb(),
        )
    else:
        await c.message.answer(
            "⚠️ Виникла технічна помилка. Спробуй ще раз пізніше або зв'яжись напряму.",
            parse_mode="HTML",
            reply_markup=main_menu_kb(),
        )

    await state.clear()


# ==========================
#    /cancel, /help
# ==========================
@dp.message(Command("cancel"))
async def cancel_cmd(m: Message, state: FSMContext):
    await state.clear()
    await m.answer("Заявку скасовано.", reply_markup=main_menu_kb())


@dp.message(Command("help"))
async def help_cmd(m: Message):
    await m.answer(
        "<b>Допомога</b>\n"
        "• /start — повернутися на початок\n"
        "• /cancel — скасувати заявку\n",
        parse_mode="HTML",
    )


# ==========================
#    Webhook + aiohttp
# ==========================
async def on_startup(app: web.Application) -> None:
    railway_domain = os.getenv("RAILWAY_PUBLIC_DOMAIN", "").strip()
    webhook_url_env = os.getenv("WEBHOOK_URL", "").strip()

    if railway_domain:
        base_url = f"https://{railway_domain}"
    elif webhook_url_env:
        base_url = webhook_url_env
    else:
        log.error("Neither RAILWAY_PUBLIC_DOMAIN nor WEBHOOK_URL is set!")
        return

    webhook_url = f"{base_url}{WEBHOOK_PATH}"
    await bot.set_webhook(webhook_url, drop_pending_updates=True)
    log.info("Webhook set: %s", webhook_url)

    info = await bot.get_webhook_info()
    log.info("Webhook verify: url=%s pending=%d error=%s",
             info.url, info.pending_update_count, info.last_error_message or "none")


async def on_shutdown(app: web.Application) -> None:
    await bot.session.close()
    log.info("Bot session closed")


def create_app() -> web.Application:
    app = web.Application()

    async def health(_: web.Request) -> web.Response:
        return web.Response(text="ok")

    app.router.add_get("/", health)

    webhook_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_handler.register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)

    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    return app


def main() -> None:
    port = int(os.getenv("PORT", "8080"))
    app = create_app()
    log.info("Starting on port %d", port)
    web.run_app(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
