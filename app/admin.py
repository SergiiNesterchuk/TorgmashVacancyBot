"""Admin panel for the vacancy bot.
Only accessible by ADMIN_ID (455473829 / @sergei_nester4uk).
"""
import asyncio
import logging
from html import escape as h

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from .services.users_db import (
    get_all_users, get_user, get_user_count,
    get_waitlist, set_waitlist, add_to_waitlist,
    remove_from_waitlist, clear_waitlist,
)

log = logging.getLogger(__name__)

ADMIN_ID = 455473829

router = Router()


class AdminState(StatesGroup):
    broadcast_all = State()        # waiting for message to send to ALL
    broadcast_selected = State()   # waiting for user IDs list
    broadcast_selected_msg = State()  # waiting for message to selected
    broadcast_waitlist = State()   # waiting for message to waitlist
    waitlist_add = State()         # waiting for IDs to add to waitlist
    waitlist_set = State()         # waiting for IDs to SET waitlist
    waitlist_remove = State()      # waiting for IDs to remove


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


def admin_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Всі користувачі", callback_data="adm:users")],
        [InlineKeyboardButton(text="📢 Розсилка ВСІМ", callback_data="adm:push_all")],
        [InlineKeyboardButton(text="📨 Розсилка ОБРАНИМ", callback_data="adm:push_selected")],
        [InlineKeyboardButton(text="📋 Вейтінг-лист", callback_data="adm:waitlist")],
        [InlineKeyboardButton(text="📢 Розсилка ВЕЙТІНГ-ЛИСТУ", callback_data="adm:push_waitlist")],
    ])


def waitlist_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Показати список", callback_data="wl:show")],
        [InlineKeyboardButton(text="➕ Додати користувачів", callback_data="wl:add")],
        [InlineKeyboardButton(text="➖ Видалити користувачів", callback_data="wl:remove")],
        [InlineKeyboardButton(text="📝 Замінити весь список", callback_data="wl:set")],
        [InlineKeyboardButton(text="🗑 Очистити список", callback_data="wl:clear")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="adm:menu")],
    ])


# ---- /admin ----

@router.message(Command("admin"))
async def admin_cmd(m: Message, state: FSMContext):
    if not is_admin(m.from_user.id):
        return
    await state.clear()
    count = get_user_count()
    wl_count = len(get_waitlist())
    await m.answer(
        f"<b>🔐 Адмін-панель</b>\n\n"
        f"Всього користувачів: <b>{count}</b>\n"
        f"У вейтінг-листі: <b>{wl_count}</b>",
        parse_mode="HTML",
        reply_markup=admin_menu_kb(),
    )


@router.callback_query(F.data == "adm:menu")
async def admin_menu_cb(c: CallbackQuery, state: FSMContext):
    if not is_admin(c.from_user.id):
        return await c.answer("Доступ заборонено", show_alert=True)
    await c.answer()
    await state.clear()
    count = get_user_count()
    wl_count = len(get_waitlist())
    await c.message.edit_text(
        f"<b>🔐 Адмін-панель</b>\n\n"
        f"Всього користувачів: <b>{count}</b>\n"
        f"У вейтінг-листі: <b>{wl_count}</b>",
        parse_mode="HTML",
        reply_markup=admin_menu_kb(),
    )


# ---- Users list ----

@router.callback_query(F.data == "adm:users")
async def show_users(c: CallbackQuery):
    if not is_admin(c.from_user.id):
        return await c.answer("Доступ заборонено", show_alert=True)
    await c.answer()

    users = get_all_users()
    if not users:
        return await c.message.edit_text(
            "Поки що немає жодного користувача.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="adm:menu")]
            ]),
        )

    lines = []
    for i, u in enumerate(users, 1):
        uid = u["user_id"]
        name = u.get("first_name", "")
        last = u.get("last_name", "")
        uname = u.get("username", "")
        full = f"{name} {last}".strip()
        uname_str = f" (@{uname})" if uname else ""
        lines.append(f"{i}. <code>{uid}</code> — {h(full)}{uname_str}")

    text = f"<b>👥 Всі користувачі ({len(users)}):</b>\n\n" + "\n".join(lines)

    # Telegram max message length
    if len(text) > 4000:
        text = text[:4000] + "\n\n<i>...обрізано</i>"

    await c.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="adm:menu")]
        ]),
    )


# ---- Broadcast ALL ----

@router.callback_query(F.data == "adm:push_all")
async def push_all_start(c: CallbackQuery, state: FSMContext):
    if not is_admin(c.from_user.id):
        return await c.answer("Доступ заборонено", show_alert=True)
    await c.answer()
    count = get_user_count()
    await c.message.edit_text(
        f"📢 <b>Розсилка ВСІМ ({count} користувачів)</b>\n\n"
        "Надішли повідомлення, яке потрібно розіслати.\n"
        "Або /cancel для скасування.",
        parse_mode="HTML",
    )
    await state.set_state(AdminState.broadcast_all)


@router.message(AdminState.broadcast_all)
async def push_all_exec(m: Message, state: FSMContext, bot: Bot):
    if not is_admin(m.from_user.id):
        return
    await state.clear()
    users = get_all_users()
    await _broadcast(bot, m, [u["user_id"] for u in users], "ВСІМ")


# ---- Broadcast SELECTED ----

@router.callback_query(F.data == "adm:push_selected")
async def push_selected_start(c: CallbackQuery, state: FSMContext):
    if not is_admin(c.from_user.id):
        return await c.answer("Доступ заборонено", show_alert=True)
    await c.answer()

    users = get_all_users()
    lines = []
    for u in users:
        uid = u["user_id"]
        name = f"{u.get('first_name', '')} {u.get('last_name', '')}".strip()
        uname = f" (@{u.get('username', '')})" if u.get("username") else ""
        lines.append(f"<code>{uid}</code> — {h(name)}{uname}")

    user_list = "\n".join(lines) if lines else "<i>порожньо</i>"

    await c.message.edit_text(
        f"📨 <b>Розсилка ОБРАНИМ</b>\n\n"
        f"Доступні користувачі:\n{user_list}\n\n"
        "Надішли ID користувачів через кому або пробіл:\n"
        "<code>123456789 987654321</code>\n\n"
        "Або /cancel для скасування.",
        parse_mode="HTML",
    )
    await state.set_state(AdminState.broadcast_selected)


@router.message(AdminState.broadcast_selected)
async def push_selected_ids(m: Message, state: FSMContext):
    if not is_admin(m.from_user.id):
        return
    text = (m.text or "").strip()
    ids = _parse_ids(text)
    if not ids:
        return await m.answer("Не вдалося розпізнати ID. Надішли числа через кому/пробіл.")

    await state.update_data(selected_ids=ids)
    await m.answer(
        f"Обрано <b>{len(ids)}</b> користувачів.\n\n"
        "Тепер надішли повідомлення для розсилки.\n"
        "Або /cancel для скасування.",
        parse_mode="HTML",
    )
    await state.set_state(AdminState.broadcast_selected_msg)


@router.message(AdminState.broadcast_selected_msg)
async def push_selected_exec(m: Message, state: FSMContext, bot: Bot):
    if not is_admin(m.from_user.id):
        return
    data = await state.get_data()
    ids = data.get("selected_ids", [])
    await state.clear()
    await _broadcast(bot, m, ids, f"ОБРАНИМ ({len(ids)})")


# ---- Broadcast WAITLIST ----

@router.callback_query(F.data == "adm:push_waitlist")
async def push_waitlist_start(c: CallbackQuery, state: FSMContext):
    if not is_admin(c.from_user.id):
        return await c.answer("Доступ заборонено", show_alert=True)
    await c.answer()
    wl = get_waitlist()
    if not wl:
        return await c.message.edit_text(
            "Вейтінг-лист порожній. Спочатку додай користувачів.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="adm:menu")]
            ]),
        )
    await c.message.edit_text(
        f"📢 <b>Розсилка ВЕЙТІНГ-ЛИСТУ ({len(wl)} осіб)</b>\n\n"
        "Надішли повідомлення для розсилки.\n"
        "Або /cancel для скасування.",
        parse_mode="HTML",
    )
    await state.set_state(AdminState.broadcast_waitlist)


@router.message(AdminState.broadcast_waitlist)
async def push_waitlist_exec(m: Message, state: FSMContext, bot: Bot):
    if not is_admin(m.from_user.id):
        return
    await state.clear()
    wl = get_waitlist()
    await _broadcast(bot, m, wl, f"ВЕЙТІНГ-ЛИСТУ ({len(wl)})")


# ---- Waitlist management ----

@router.callback_query(F.data == "adm:waitlist")
async def waitlist_menu(c: CallbackQuery, state: FSMContext):
    if not is_admin(c.from_user.id):
        return await c.answer("Доступ заборонено", show_alert=True)
    await c.answer()
    await state.clear()
    wl = get_waitlist()
    await c.message.edit_text(
        f"<b>📋 Вейтінг-лист ({len(wl)} осіб)</b>",
        parse_mode="HTML",
        reply_markup=waitlist_menu_kb(),
    )


@router.callback_query(F.data == "wl:show")
async def wl_show(c: CallbackQuery):
    if not is_admin(c.from_user.id):
        return await c.answer("Доступ заборонено", show_alert=True)
    await c.answer()
    wl = get_waitlist()
    if not wl:
        text = "Вейтінг-лист порожній."
    else:
        lines = []
        for uid in wl:
            u = get_user(uid)
            if u:
                name = f"{u.get('first_name', '')} {u.get('last_name', '')}".strip()
                uname = f" (@{u.get('username', '')})" if u.get("username") else ""
                lines.append(f"<code>{uid}</code> — {h(name)}{uname}")
            else:
                lines.append(f"<code>{uid}</code> — <i>невідомий</i>")
        text = f"<b>📋 Вейтінг-лист ({len(wl)}):</b>\n\n" + "\n".join(lines)

    await c.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="adm:waitlist")]
        ]),
    )


@router.callback_query(F.data == "wl:add")
async def wl_add_start(c: CallbackQuery, state: FSMContext):
    if not is_admin(c.from_user.id):
        return await c.answer("Доступ заборонено", show_alert=True)
    await c.answer()

    # Show available users for easy copy
    users = get_all_users()
    wl = get_waitlist()
    available = [u for u in users if u["user_id"] not in wl]

    if available:
        lines = [f"<code>{u['user_id']}</code> — {h(u.get('first_name',''))} {h(u.get('last_name',''))}".strip()
                 for u in available]
        avail_text = "\n".join(lines)
    else:
        avail_text = "<i>всі вже у списку</i>"

    await c.message.edit_text(
        f"➕ <b>Додати до вейтінг-листа</b>\n\n"
        f"Доступні користувачі (НЕ в списку):\n{avail_text}\n\n"
        "Надішли ID через кому/пробіл:\n"
        "<code>123456789 987654321</code>\n\n"
        "/cancel для скасування.",
        parse_mode="HTML",
    )
    await state.set_state(AdminState.waitlist_add)


@router.message(AdminState.waitlist_add)
async def wl_add_exec(m: Message, state: FSMContext):
    if not is_admin(m.from_user.id):
        return
    await state.clear()
    ids = _parse_ids(m.text or "")
    if not ids:
        return await m.answer("Не вдалося розпізнати ID.")
    for uid in ids:
        add_to_waitlist(uid)
    await m.answer(f"✅ Додано {len(ids)} користувачів до вейтінг-листа.\n\n/admin — повернутися.")


@router.callback_query(F.data == "wl:remove")
async def wl_remove_start(c: CallbackQuery, state: FSMContext):
    if not is_admin(c.from_user.id):
        return await c.answer("Доступ заборонено", show_alert=True)
    await c.answer()
    wl = get_waitlist()
    if not wl:
        return await c.message.edit_text(
            "Вейтінг-лист вже порожній.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="adm:waitlist")]
            ]),
        )

    lines = []
    for uid in wl:
        u = get_user(uid)
        name = f"{u.get('first_name','')} {u.get('last_name','')}".strip() if u else "невідомий"
        lines.append(f"<code>{uid}</code> — {h(name)}")

    await c.message.edit_text(
        f"➖ <b>Видалити з вейтінг-листа</b>\n\n"
        f"Зараз у списку:\n" + "\n".join(lines) + "\n\n"
        "Надішли ID для видалення:\n"
        "<code>123456789 987654321</code>\n\n"
        "/cancel для скасування.",
        parse_mode="HTML",
    )
    await state.set_state(AdminState.waitlist_remove)


@router.message(AdminState.waitlist_remove)
async def wl_remove_exec(m: Message, state: FSMContext):
    if not is_admin(m.from_user.id):
        return
    await state.clear()
    ids = _parse_ids(m.text or "")
    if not ids:
        return await m.answer("Не вдалося розпізнати ID.")
    for uid in ids:
        remove_from_waitlist(uid)
    await m.answer(f"✅ Видалено {len(ids)} користувачів з вейтінг-листа.\n\n/admin — повернутися.")


@router.callback_query(F.data == "wl:set")
async def wl_set_start(c: CallbackQuery, state: FSMContext):
    if not is_admin(c.from_user.id):
        return await c.answer("Доступ заборонено", show_alert=True)
    await c.answer()

    users = get_all_users()
    lines = [f"<code>{u['user_id']}</code> — {h(u.get('first_name',''))} {h(u.get('last_name',''))}".strip()
             for u in users]
    avail_text = "\n".join(lines) if lines else "<i>порожньо</i>"

    await c.message.edit_text(
        f"📝 <b>Замінити весь вейтінг-лист</b>\n\n"
        f"Всі користувачі:\n{avail_text}\n\n"
        "Надішли ID нового списку:\n"
        "<code>123456789 987654321</code>\n\n"
        "Це ЗАМІНИТЬ весь поточний список!\n"
        "/cancel для скасування.",
        parse_mode="HTML",
    )
    await state.set_state(AdminState.waitlist_set)


@router.message(AdminState.waitlist_set)
async def wl_set_exec(m: Message, state: FSMContext):
    if not is_admin(m.from_user.id):
        return
    await state.clear()
    ids = _parse_ids(m.text or "")
    if not ids:
        return await m.answer("Не вдалося розпізнати ID.")
    set_waitlist(ids)
    await m.answer(f"✅ Вейтінг-лист замінено. Нових записів: {len(ids)}.\n\n/admin — повернутися.")


@router.callback_query(F.data == "wl:clear")
async def wl_clear(c: CallbackQuery):
    if not is_admin(c.from_user.id):
        return await c.answer("Доступ заборонено", show_alert=True)
    await c.answer()
    clear_waitlist()
    await c.message.edit_text(
        "🗑 Вейтінг-лист очищено.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="adm:waitlist")]
        ]),
    )


# ---- Cancel (works in any admin state) ----

@router.message(Command("cancel"))
async def admin_cancel(m: Message, state: FSMContext):
    current = await state.get_state()
    if current and current.startswith("AdminState:"):
        await state.clear()
        await m.answer("Скасовано.\n/admin — повернутися до адмін-панелі.")


# ---- Helpers ----

def _parse_ids(text: str) -> list[int]:
    """Parse user IDs from text (comma, space, newline separated)."""
    ids = []
    for part in text.replace(",", " ").replace("\n", " ").split():
        part = part.strip()
        try:
            ids.append(int(part))
        except ValueError:
            continue
    return ids


async def _broadcast(bot: Bot, m: Message, user_ids: list[int], label: str):
    """Forward admin's message to list of users."""
    if not user_ids:
        return await m.answer("Список порожній, нікому надсилати.")

    status = await m.answer(f"⏳ Розсилка {label}... (0/{len(user_ids)})")
    sent = 0
    failed = 0
    blocked = 0

    for uid in user_ids:
        try:
            await m.copy_to(uid)
            sent += 1
        except Exception as e:
            err = str(e).lower()
            if "blocked" in err or "deactivated" in err or "not found" in err:
                blocked += 1
            else:
                failed += 1
                log.warning("Broadcast to %d failed: %s", uid, e)
        # Rate limit: 30 msg/sec max for Telegram
        await asyncio.sleep(0.05)

    result = (
        f"✅ <b>Розсилка {h(label)} завершена!</b>\n\n"
        f"📤 Надіслано: <b>{sent}</b>\n"
        f"🚫 Заблоковані: <b>{blocked}</b>\n"
        f"❌ Помилки: <b>{failed}</b>"
    )
    try:
        await status.edit_text(result, parse_mode="HTML")
    except Exception:
        await m.answer(result, parse_mode="HTML")
