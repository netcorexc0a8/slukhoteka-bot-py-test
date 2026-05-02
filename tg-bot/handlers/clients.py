"""
Раздел «👤 Клиенты».

Карточка клиента объединяет:
- список абонементов со статусами
- ближайшее занятие
- действия: записать на занятие, выдать абонемент, передать (admin/methodist)

Поток:
  «👤 Клиенты» → список → карточка клиента
    ↓
  [➕ Записать]       → переход в flow создания записи (schedule_create)
  [🎫 Выдать абонемент] → переход в flow выдачи (subs_issue_start)
  [🔁 Передать]       → выбор нового владельца (admin/methodist)
  [⬅️ Назад]
"""
import logging
from utils.errors import friendly_error
from datetime import datetime
from utils.dt import now as dt_now
from typing import Optional

import httpx
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery, Message,
    InlineKeyboardButton, InlineKeyboardMarkup,
)

from services.api_client import BackendAPIClient

router = Router()
logger = logging.getLogger(__name__)

DAY_SHORT = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
PAGE_SIZE = 10  # клиентов на страницу


class ClientsState(StatesGroup):
    select_client = State()
    client_card = State()
    transfer_select_owner = State()


# =====================================================================
# Точка входа
# =====================================================================

@router.callback_query(F.data == "clients_menu")
async def clients_menu(callback: CallbackQuery, state: FSMContext):
    # Сбрасываем кеш, чтобы список всегда был актуальным
    await state.update_data(cl_clients_cache=None)
    await _show_clients_list(callback, state, page=0)


@router.callback_query(F.data.startswith("cl_page_"))
async def clients_page(callback: CallbackQuery, state: FSMContext):
    page = int(callback.data.split("_")[-1])
    await _show_clients_list(callback, state, page=page)
    await callback.answer()


async def _show_clients_list(callback: CallbackQuery, state: FSMContext, page: int = 0):
    user_data = await state.get_data()
    specialist_id = user_data.get("global_user_id")
    role = user_data.get("role", "specialist")

    # Берём кеш или загружаем заново
    clients = user_data.get("cl_clients_cache")
    if clients is None:
        api = BackendAPIClient()
        try:
            uid = None if role in ("admin", "methodist") else specialist_id
            clients = await api.clients_get_all(user_id=uid)
        except Exception as e:
            logger.exception("clients list error")
            await callback.message.edit_text(friendly_error(e, "clients"))
            return

        clients = [c for c in clients if not c.get("deleted_at")]
        clients.sort(key=lambda c: (c.get("name") or "").lower())
        await state.update_data(cl_clients_cache=clients)

    if not clients:
        await callback.message.edit_text(
            "Клиентов пока нет.\n"
            "Клиент создаётся автоматически при первой записи или выдаче абонемента.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="⬅️ В меню расписания", callback_data="sched_back_to_main")
            ]]),
        )
        return

    total = len(clients)
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))

    page_clients = clients[page * PAGE_SIZE : (page + 1) * PAGE_SIZE]

    buttons = []
    for i, c in enumerate(page_clients):
        global_idx = page * PAGE_SIZE + i
        label = c.get("name") or "—"
        if len(label) > 50:
            label = label[:47] + "…"
        buttons.append([InlineKeyboardButton(
            text=label,
            callback_data=f"cl_pick_{global_idx}",
        )])

    # Навигация по страницам
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"cl_page_{page - 1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="Вперёд ▶️", callback_data=f"cl_page_{page + 1}"))
    if nav:
        buttons.append(nav)

    buttons.append([InlineKeyboardButton(text="⬅️ В меню расписания", callback_data="sched_back_to_main")])

    page_label = f" (стр. {page + 1}/{total_pages})" if total_pages > 1 else ""
    await callback.message.edit_text(
        f"👤 Клиенты ({total}){page_label}:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await state.set_state(ClientsState.select_client)


# =====================================================================
# Карточка клиента
# =====================================================================

@router.callback_query(F.data.startswith("cl_pick_"), ClientsState.select_client)
async def cl_pick(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.rsplit("_", 1)[-1])
    user_data = await state.get_data()
    clients = user_data.get("cl_clients_cache") or []
    if idx >= len(clients):
        await callback.answer("Клиент не найден.", show_alert=True)
        return
    client = clients[idx]
    await state.update_data(
        cl_client_id=client["id"],
        cl_client_name=client["name"],
        cl_client_owner_id=client.get("global_user_id"),
    )
    await _show_client_card(callback, state)
    await callback.answer()


async def _show_client_card(callback: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    client_id = user_data["cl_client_id"]
    client_name = user_data.get("cl_client_name") or "—"
    role = user_data.get("role", "specialist")
    specialist_id = user_data.get("global_user_id")

    api = BackendAPIClient()

    # Абонементы
    try:
        subs = await api.subscriptions_for_client(client_id=client_id)
    except Exception:
        subs = []

    # Ближайшая бронь — смотрим 90 дней вперёд
    try:
        today = dt_now()
        start_date = today.strftime("%Y-%m-%d")
        end_date = today.replace(year=today.year + 1).strftime("%Y-%m-%d")
        bookings = await api.bookings_for_range(
            start_date=start_date,
            end_date=end_date,
            client_id=client_id,
        )
        future = [
            b for b in (bookings or [])
            if not b.get("deleted_at")
            and b.get("status") == "scheduled"
        ]
        future.sort(key=lambda b: b["start_time"])
        next_booking = future[0] if future else None
    except Exception:
        next_booking = None

    # Строим текст карточки
    lines = [f"👤 <b>{client_name}</b>", ""]

    if next_booking:
        try:
            d = datetime.strptime(next_booking["start_time"][:10], "%Y-%m-%d")
            wd = DAY_SHORT[d.weekday()]
            date_label = f"{d.strftime('%d.%m.%Y')} ({wd})"
        except Exception:
            date_label = next_booking["start_time"][:10]
        time_str = next_booking["start_time"][11:16]
        lines.append(f"📅 Ближайшее: {date_label} в {time_str}")
        lines.append("")

    if subs:
        lines.append("🎫 Абонементы:")
        status_emoji = {
            "active": "🟢", "completed": "✅",
            "expired": "⏰", "cancelled": "⛔",
        }
        for s in sorted(subs, key=lambda s: s.get("purchased_at") or "", reverse=True):
            sname = s.get("service_name") or s.get("service_type") or ""
            used = s.get("used_sessions", 0)
            total = s.get("total_sessions", 0)
            emoji = status_emoji.get(s.get("status", ""), "•")
            spec = s.get("assigned_specialist_name") or ""
            group = s.get("group_name") or ""
            purchased = (s.get("purchased_at") or "")[:10]
            try:
                purchased_h = datetime.strptime(purchased, "%Y-%m-%d").strftime("%d.%m.%Y")
            except Exception:
                purchased_h = purchased

            line = f"{emoji} {sname} — {used}/{total}"
            if group:
                line += f" — 👥 {group}"
            elif spec:
                line += f" — {spec}"
            if purchased_h:
                line += f" (от {purchased_h})"
            lines.append(line)
    else:
        lines.append("Абонементов нет.")

    # Кнопки
    buttons = [
        [InlineKeyboardButton(text="➕ Записать на занятие", callback_data=f"cl_to_schedule_{client_id}")],
        [InlineKeyboardButton(text="🎫 Выдать абонемент", callback_data=f"cl_to_issue_{client_id}")],
    ]
    if role in ("admin", "methodist"):
        buttons.append([InlineKeyboardButton(
            text="🔁 Передать клиента",
            callback_data=f"cl_transfer_{client_id}",
        )])
    buttons.append([InlineKeyboardButton(text="⬅️ К списку клиентов", callback_data="clients_menu")])

    await callback.message.edit_text(
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await state.set_state(ClientsState.client_card)


# =====================================================================
# Кнопки действий из карточки
# =====================================================================

@router.callback_query(F.data.startswith("cl_to_schedule_"), ClientsState.client_card)
async def cl_to_schedule(callback: CallbackQuery, state: FSMContext):
    """Перебрасываем в flow создания записи, предзаполнив клиента."""
    client_id = int(callback.data.rsplit("_", 1)[-1])
    user_data = await state.get_data()
    client_name = user_data.get("cl_client_name") or ""
    await state.update_data(
        create_client_id=client_id,
        create_client_name=client_name,
    )
    from handlers.schedule import _show_subscriptions_for_create, _FakeCallback
    fake = _FakeCallback(message=callback.message)
    await _show_subscriptions_for_create(fake, state)
    await callback.answer()


@router.callback_query(F.data.startswith("cl_to_issue_"), ClientsState.client_card)
async def cl_to_issue(callback: CallbackQuery, state: FSMContext):
    """Перебрасываем в flow выдачи абонемента, предзаполнив клиента."""
    client_id = int(callback.data.rsplit("_", 1)[-1])
    user_data = await state.get_data()
    client_name = user_data.get("cl_client_name") or ""
    await state.update_data(
        subs_client_id=client_id,
        subs_client_name=client_name,
    )
    from handlers.subscriptions import subs_issue_start
    await subs_issue_start(callback, state)
    await callback.answer()


# =====================================================================
# Передача клиента
# =====================================================================

@router.callback_query(F.data.startswith("cl_transfer_"), ClientsState.client_card)
async def cl_transfer_start(callback: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    role = user_data.get("role", "specialist")
    if role not in ("admin", "methodist"):
        await callback.answer("Недостаточно прав.", show_alert=True)
        return

    client_id = int(callback.data.rsplit("_", 1)[-1])
    client_name = user_data.get("cl_client_name") or "клиента"
    current_owner_id = user_data.get("cl_client_owner_id")

    api = BackendAPIClient()

    try:
        check = await api.client_can_transfer(client_id)
    except Exception as e:
        logger.exception("can_transfer error")
        await callback.message.edit_text(friendly_error(e, "clients"))
        await callback.answer()
        return

    if not check.get("can_transfer"):
        await callback.message.edit_text(
            f"Передача невозможна.\n\n{check.get('reason', '')}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="⬅️ Назад", callback_data="clients_menu")
            ]]),
        )
        await callback.answer()
        return

    try:
        users = await api.users_get_all()
    except Exception as e:
        logger.exception("users_get_all error")
        await callback.message.edit_text(friendly_error(e, "clients"))
        await callback.answer()
        return

    candidates = [
        u for u in users
        if u.get("role") in ("specialist", "methodist", "admin")
        and not u.get("deleted_at")
        and u.get("is_active", True)
        and u.get("id") != current_owner_id
    ]
    candidates.sort(key=lambda u: (u.get("name") or "").lower())

    if not candidates:
        await callback.message.edit_text(
            "Нет доступных специалистов для передачи.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="⬅️ Назад", callback_data="clients_menu")
            ]]),
        )
        await callback.answer()
        return

    await state.update_data(
        cl_transfer_client_id=client_id,
        cl_transfer_client_name=client_name,
        cl_transfer_candidates=candidates,
    )

    buttons = []
    for i, u in enumerate(candidates):
        label = u.get("name") or u.get("phone") or f"id={u['id']}"
        role_label = {"admin": "админ", "methodist": "методист", "specialist": "специалист"}.get(
            u.get("role"), ""
        )
        if role_label:
            label = f"{label} ({role_label})"
        buttons.append([InlineKeyboardButton(
            text=label[:64],
            callback_data=f"cl_transfer_to_{i}",
        )])
    buttons.append([InlineKeyboardButton(text="⬅️ Отмена", callback_data="clients_menu")])

    await callback.message.edit_text(
        f"🔁 Передать клиента «{client_name}»\n\nКому передаём?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await state.set_state(ClientsState.transfer_select_owner)
    await callback.answer()


@router.callback_query(F.data.startswith("cl_transfer_to_"), ClientsState.transfer_select_owner)
async def cl_transfer_to(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.rsplit("_", 1)[-1])
    user_data = await state.get_data()

    candidates = user_data.get("cl_transfer_candidates") or []
    if idx >= len(candidates):
        await callback.answer("Специалист не найден.", show_alert=True)
        return

    new_owner = candidates[idx]
    client_id = user_data.get("cl_transfer_client_id")
    client_name = user_data.get("cl_transfer_client_name") or "клиент"

    api = BackendAPIClient()
    try:
        await api.client_transfer(client_id=client_id, new_owner_id=new_owner["id"])
    except httpx.HTTPStatusError as e:
        detail = ""
        try:
            detail = e.response.json().get("detail", "")
        except Exception:
            pass
        await callback.message.edit_text(
            f"Не удалось передать:\n{detail or e}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="⬅️ К клиентам", callback_data="clients_menu")
            ]]),
        )
        await callback.answer()
        return
    except Exception as e:
        logger.exception("client_transfer error")
        await callback.message.edit_text(friendly_error(e, "clients"))
        await callback.answer()
        return

    new_owner_name = new_owner.get("name") or new_owner.get("phone") or "?"
    await callback.message.edit_text(
        f"✅ Клиент «{client_name}» передан специалисту «{new_owner_name}».",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="⬅️ К клиентам", callback_data="clients_menu")
        ]]),
    )
    await state.set_state(ClientsState.select_client)
    await callback.answer("Передан")