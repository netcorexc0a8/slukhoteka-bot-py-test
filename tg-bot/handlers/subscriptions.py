"""
Раздел "Абонементы" в боте.

Возможности:
- Список клиентов → абонементы конкретного клиента → выдача нового / отмена
- Также используется в процессе создания записи: если у клиента нет
  активного абонемента, мы запускаем mini-flow выдачи и возвращаем
  пользователя обратно к выбору абонемента.
"""
import logging

import httpx
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from services.api_client import BackendAPIClient

router = Router()
logger = logging.getLogger(__name__)


class SubscriptionState(StatesGroup):
    main = State()
    select_client = State()
    client_subscriptions = State()
    issue_select_service = State()


# Маркер, как продолжить flow после выдачи: "create_record" — вернуться в schedule.create
# или None — остаться в разделе абонементов.
RETURN_KEY = "subscriptions_return_to"


# =====================================================================
# Главный экран "Абонементы" (callback из меню расписания)
# =====================================================================

@router.callback_query(F.data == "subscriptions_menu")
async def subscriptions_menu(callback: CallbackQuery, state: FSMContext):
    """Открывает раздел абонементов: показывает список клиентов."""
    await _show_clients_list(callback, state, return_to=None)
    await callback.answer()


async def _show_clients_list(callback: CallbackQuery, state: FSMContext, return_to: str | None):
    user_data = await state.get_data()
    specialist_id = user_data.get("global_user_id")

    try:
        api = BackendAPIClient()
        clients = await api.clients_get_all(user_id=specialist_id)
    except Exception as e:
        logger.exception("subs: clients fetch error")
        await callback.message.edit_text(f"Ошибка загрузки клиентов: {e}")
        return

    clients = [c for c in clients if not c.get("deleted_at")]
    clients.sort(key=lambda c: (c.get("name") or "").lower())

    await state.update_data(subs_clients_cache=clients, **{RETURN_KEY: return_to})

    if not clients:
        await callback.message.edit_text(
            "У вас пока нет клиентов.\n"
            "Создать клиента можно при оформлении первой записи.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="⬅️ Назад", callback_data="sched_back_to_main")
            ]]),
        )
        await state.set_state(SubscriptionState.main)
        return

    buttons = []
    for i, c in enumerate(clients):
        label = c.get("name", "Без имени")
        if len(label) > 50:
            label = label[:47] + "…"
        buttons.append([InlineKeyboardButton(
            text=label,
            callback_data=f"subs_client_{i}",
        )])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="sched_back_to_main")])

    await callback.message.edit_text(
        "🎫 Абонементы\n\nВыберите клиента:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await state.set_state(SubscriptionState.select_client)


@router.callback_query(F.data.startswith("subs_client_"), SubscriptionState.select_client)
async def subs_client_picked(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.rsplit("_", 1)[-1])
    user_data = await state.get_data()
    clients = user_data.get("subs_clients_cache") or []
    if idx >= len(clients):
        await callback.answer("Клиент не найден.", show_alert=True)
        return
    client = clients[idx]
    await state.update_data(
        subs_client_id=client["id"],
        subs_client_name=client["name"],
    )
    await _show_subs_for_client(callback, state)
    await callback.answer()


async def _show_subs_for_client(callback: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    client_id = user_data["subs_client_id"]
    client_name = user_data.get("subs_client_name", "")

    try:
        api = BackendAPIClient()
        subs = await api.subscriptions_for_client(client_id=client_id)
    except Exception as e:
        logger.exception("subs fetch error")
        await callback.message.edit_text(f"Ошибка: {e}")
        return

    subs.sort(key=lambda s: s.get("purchased_at", ""), reverse=True)

    lines = [f"🎫 Абонементы клиента «{client_name}»:", ""]
    if not subs:
        lines.append("Абонементов нет.")
    else:
        for s in subs:
            sname = s.get("service_name") or s.get("service_type", "")
            status = s.get("status", "")
            used = s.get("used_sessions", 0)
            total = s.get("total_sessions", 0)
            spec = s.get("assigned_specialist_name") or "—"
            status_emoji = {
                "active": "🟢", "completed": "✅", "expired": "⏰", "cancelled": "⛔",
            }.get(status, "•")
            line = f"{status_emoji} {sname} — {used}/{total}"
            if spec and spec != "—":
                line += f" — {spec}"
            lines.append(line)

    text = "\n".join(lines)

    buttons = [
        [InlineKeyboardButton(text="🎫 Выдать новый абонемент", callback_data="subs_issue_start")],
        [InlineKeyboardButton(text="⬅️ Назад к клиентам", callback_data="subscriptions_menu")],
    ]

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await state.set_state(SubscriptionState.client_subscriptions)


# =====================================================================
# Выдача абонемента
# =====================================================================

@router.callback_query(F.data == "subs_issue_start")
async def subs_issue_start(callback: CallbackQuery, state: FSMContext):
    """Шаг 1 выдачи: выбираем услугу из справочника."""
    try:
        api = BackendAPIClient()
        services = await api.services_list()
    except Exception as e:
        logger.exception("services_list error")
        await callback.message.edit_text(f"Ошибка: {e}")
        return

    # На этом этапе скрываем алгоритмику (групповая) — отложили
    services = [s for s in services if not s.get("is_group")]

    buttons = []
    for s in services:
        label = f"{s['name']} ({s['max_sessions']} сесс.)"
        buttons.append([InlineKeyboardButton(
            text=label,
            callback_data=f"subs_issue_pick_{s['id']}",
        )])
    buttons.append([InlineKeyboardButton(text="⬅️ Отмена", callback_data="subs_issue_cancel")])

    await callback.message.edit_text(
        "Выберите тип абонемента:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await state.set_state(SubscriptionState.issue_select_service)
    await callback.answer()


@router.callback_query(F.data == "subs_issue_cancel")
async def subs_issue_cancel(callback: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    return_to = user_data.get(RETURN_KEY)
    if return_to == "create_record":
        # Возвращаемся к выбору абонемента в потоке создания записи
        from handlers.schedule import _show_subscriptions_for_create, ScheduleState
        await state.set_state(ScheduleState.create_select_subscription)
        await _show_subscriptions_for_create(callback, state)
    else:
        await _show_subs_for_client(callback, state)
    await callback.answer()


@router.callback_query(F.data.startswith("subs_issue_pick_"), SubscriptionState.issue_select_service)
async def subs_issue_pick(callback: CallbackQuery, state: FSMContext):
    """Создаём абонемент: индивидуальный, специалист = текущий пользователь."""
    service_id = int(callback.data.rsplit("_", 1)[-1])
    user_data = await state.get_data()
    client_id = user_data["subs_client_id"]
    specialist_id = user_data.get("global_user_id")

    try:
        api = BackendAPIClient()
        sub = await api.subscription_create(
            client_id=client_id,
            service_id=service_id,
            assigned_specialist_id=specialist_id,
        )
    except httpx.HTTPStatusError as e:
        detail = ""
        try:
            detail = e.response.json().get("detail", "")
        except Exception:
            pass
        await callback.message.edit_text(f"Не удалось выдать абонемент:\n{detail or e}")
        await callback.answer()
        return
    except Exception as e:
        logger.exception("subscription_create error")
        await callback.message.edit_text(f"Ошибка: {e}")
        await callback.answer()
        return

    service_name = sub.get("service_name") or "Абонемент"
    total = sub.get("total_sessions")
    text = (
        f"✅ Выдан абонемент:\n"
        f"{service_name} ({total} сесс.)\n"
        f"Клиент: {user_data.get('subs_client_name', '')}"
    )

    return_to = user_data.get(RETURN_KEY)
    if return_to == "create_record":
        # Идём дальше по flow создания записи: показать абонементы и продолжить
        await callback.message.edit_text(text)
        from handlers.schedule import _show_subscriptions_for_create, ScheduleState
        await state.set_state(ScheduleState.create_select_subscription)
        # Перерисуем как новое сообщение, чтобы не потерять подтверждение выше
        new_msg = await callback.message.answer("…")

        class _C:
            def __init__(self, m): self.message = m
            async def answer(self, *a, **k): return None

        await _show_subscriptions_for_create(_C(new_msg), state)
    else:
        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="⬅️ К абонементам клиента", callback_data="subs_back_client")
            ]]),
        )
    await callback.answer("Готово")


@router.callback_query(F.data == "subs_back_client")
async def subs_back_client(callback: CallbackQuery, state: FSMContext):
    await _show_subs_for_client(callback, state)
    await callback.answer()


# =====================================================================
# Внешний API для schedule.py — запуск мини-flow выдачи изнутри создания
# =====================================================================

async def start_issue_flow_inline(
    callback: CallbackQuery,
    state: FSMContext,
    *,
    client_id: int,
    client_name: str,
    return_to: str = "create_record",
) -> None:
    """
    Запускает мини-flow выдачи абонемента посреди flow создания записи.
    После выдачи (или отмены) пользователь вернётся к выбору абонемента.
    """
    await state.update_data(
        subs_client_id=client_id,
        subs_client_name=client_name,
        **{RETURN_KEY: return_to},
    )
    await subs_issue_start(callback, state)
