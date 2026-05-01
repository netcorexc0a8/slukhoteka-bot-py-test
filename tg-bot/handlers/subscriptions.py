"""
Раздел "Абонементы" в боте.

Поддерживает выдачу 5 типов абонементов:
- Индивидуальные (диагностика / 1 / 4 / 8 дней) — закрепляются за специалистом
- Алгоритмика — групповой, требует выбора группы

Используется и из главного меню расписания ("🎫 Абонементы"), и изнутри
flow создания записи (если у клиента нет нужного абонемента).
"""
import logging
from datetime import datetime

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
    issue_select_group = State()  # для алгоритмики — выбор группы
    cancel_select_sub = State()
    cancel_confirm = State()
    transfer_select_owner = State()  # выбор нового владельца клиента


RETURN_KEY = "subscriptions_return_to"


# =====================================================================
# Главный экран
# =====================================================================

@router.callback_query(F.data == "subscriptions_menu")
async def subscriptions_menu(callback: CallbackQuery, state: FSMContext):
    await _show_clients_list(callback, state, return_to=None)
    await callback.answer()


async def _show_clients_list(callback: CallbackQuery, state: FSMContext, return_to: str | None):
    user_data = await state.get_data()
    specialist_id = user_data.get("global_user_id")
    role = user_data.get("role", "specialist")

    try:
        api = BackendAPIClient()
        # admin/methodist видят всех, specialist — только своих
        uid = None if role in ("admin", "methodist") else specialist_id
        clients = await api.clients_get_all(user_id=uid)
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
        subs_client_owner_id=client.get("global_user_id"),
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
            spec = s.get("assigned_specialist_name") or ""
            group = s.get("group_name") or ""
            purchased = (s.get("purchased_at") or "")[:10]
            # YYYY-MM-DD → DD.MM.YYYY
            try:
                purchased_human = datetime.strptime(purchased, "%Y-%m-%d").strftime("%d.%m.%Y")
            except Exception:
                purchased_human = purchased

            status_emoji = {
                "active": "🟢", "completed": "✅", "expired": "⏰", "cancelled": "⛔",
            }.get(status, "•")
            line = f"{status_emoji} {sname} — {used}/{total}"
            if group:
                line += f" — 👥 {group}"
            elif spec:
                line += f" — {spec}"
            if purchased_human:
                line += f" (от {purchased_human})"
            lines.append(line)

    text = "\n".join(lines)

    buttons = []
    for s in subs:
        if s.get("status") == "active":
            remaining = s.get("remaining_sessions", 0)
            total = s.get("total_sessions", 0)
            purchased = (s.get("purchased_at") or "")[:10]  # YYYY-MM-DD
            sname = s.get("service_name") or s.get("service_type") or ""
            if len(sname) > 20:
                sname = sname[:20] + "…"
            label = f"❌ {sname} {remaining}/{total} от {purchased}"
            buttons.append([InlineKeyboardButton(
                text=label[:64],
                callback_data=f"subs_cancel_{s['id']}",
            )])
    buttons.append([InlineKeyboardButton(text="🎫 Выдать новый абонемент", callback_data="subs_issue_start")])

    # Кнопка передачи — только для admin/methodist
    role = user_data.get("role", "specialist")
    if role in ("admin", "methodist"):
        buttons.append([InlineKeyboardButton(
            text="🔁 Передать клиента",
            callback_data=f"subs_transfer_{client_id}",
        )])

    buttons.append([InlineKeyboardButton(text="⬅️ Назад к клиентам", callback_data="subscriptions_menu")])

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
    """Шаг 1 выдачи: выбор услуги."""
    try:
        api = BackendAPIClient()
        services = await api.services_list()
    except Exception as e:
        logger.exception("services_list error")
        await callback.message.edit_text(f"Ошибка: {e}")
        return

    # Кэшируем для дальнейшего использования
    await state.update_data(subs_services_cache=services)

    buttons = []
    for s in services:
        emoji = "👥" if s.get("is_group") else "👤"
        label = f"{emoji} {s['name']} ({s['max_sessions']} зан.)"
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
        from handlers.schedule import _show_subscriptions_for_create, ScheduleState
        await state.set_state(ScheduleState.create_select_subscription)
        await _show_subscriptions_for_create(callback, state)
    else:
        await _show_subs_for_client(callback, state)
    await callback.answer()


@router.callback_query(F.data.startswith("subs_issue_pick_"), SubscriptionState.issue_select_service)
async def subs_issue_pick(callback: CallbackQuery, state: FSMContext):
    """Шаг 2: если групповая — спрашиваем группу, иначе создаём сразу."""
    service_id = int(callback.data.rsplit("_", 1)[-1])
    user_data = await state.get_data()
    services = user_data.get("subs_services_cache") or []
    service = next((s for s in services if s["id"] == service_id), None)
    if not service:
        await callback.answer("Услуга не найдена.", show_alert=True)
        return

    await state.update_data(subs_issue_service_id=service_id, subs_issue_service=service)

    if service.get("is_group"):
        # Алгоритмика — нужен выбор группы
        await _show_groups_for_issue(callback, state)
    else:
        # Индивидуальный — создаём сразу
        await _create_subscription_individual(callback, state, service_id)
    await callback.answer()


async def _show_groups_for_issue(callback: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    service_id = user_data.get("subs_issue_service_id")
    try:
        api = BackendAPIClient()
        groups = await api.groups_list(service_id=service_id)
    except Exception as e:
        logger.exception("groups_list error")
        await callback.message.edit_text(f"Ошибка: {e}")
        return

    groups = [g for g in groups if not g.get("deleted_at") and g.get("is_active", True)]
    groups.sort(key=lambda g: (g.get("name") or "").lower())

    if not groups:
        await callback.message.edit_text(
            "Нет активных групп для этой услуги.\n"
            "Сначала создайте группу в разделе «👥 Группы».",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="⬅️ Назад", callback_data="subs_issue_start")
            ]]),
        )
        return

    await state.update_data(subs_issue_groups_cache=groups)

    buttons = []
    for i, g in enumerate(groups):
        active_count = sum(1 for p in (g.get("participants") or []) if p.get("is_active"))
        max_part = g.get("max_participants", 6)
        label = f"{g.get('name', '?')} ({active_count}/{max_part})"
        if active_count >= max_part:
            label = f"⚠️ {label} полная"
        if len(label) > 50:
            label = label[:47] + "…"
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"subs_issue_grp_{i}")])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="subs_issue_start")])

    service = user_data.get("subs_issue_service") or {}
    service_name = service.get("name") or "групповой абонемент"
    await callback.message.edit_text(
        f"Выберите группу для абонемента «{service_name}»:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await state.set_state(SubscriptionState.issue_select_group)


@router.callback_query(F.data.startswith("subs_issue_grp_"), SubscriptionState.issue_select_group)
async def subs_issue_grp_picked(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.rsplit("_", 1)[-1])
    user_data = await state.get_data()
    groups = user_data.get("subs_issue_groups_cache") or []
    if idx >= len(groups):
        await callback.answer("Группа не найдена.", show_alert=True)
        return
    group = groups[idx]
    service_id = user_data.get("subs_issue_service_id")
    client_id = user_data["subs_client_id"]

    api = BackendAPIClient()
    # Дополнительно: добавляем клиента в состав группы (если ещё не там)
    try:
        await api.group_add_participant(group["id"], client_id)
    except Exception as e:
        logger.warning(f"group_add_participant warn: {e}")

    # Создаём абонемент
    try:
        sub = await api.subscription_create(
            client_id=client_id,
            service_id=service_id,
            group_id=group["id"],
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

    await _after_issue_success(callback, state, sub, group_name=group["name"])


async def _create_subscription_individual(
    callback: CallbackQuery, state: FSMContext, service_id: int,
):
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
        return
    except Exception as e:
        logger.exception("subscription_create error")
        await callback.message.edit_text(f"Ошибка: {e}")
        return

    await _after_issue_success(callback, state, sub)


async def _after_issue_success(callback, state: FSMContext, sub: dict, group_name: str | None = None):
    user_data = await state.get_data()
    service_name = sub.get("service_name") or "Абонемент"
    total = sub.get("total_sessions")

    text_lines = [
        f"✅ Выдан абонемент:",
        f"{service_name} ({total} зан.)",
        f"Клиент: {user_data.get('subs_client_name', '')}",
    ]
    if group_name:
        text_lines.append(f"Группа: {group_name}")
    text = "\n".join(text_lines)

    return_to = user_data.get(RETURN_KEY)
    if return_to == "create_record":
        await callback.message.edit_text(text)
        from handlers.schedule import _show_subscriptions_for_create, ScheduleState
        await state.set_state(ScheduleState.create_select_subscription)
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


@router.callback_query(F.data.startswith("subs_cancel_"), SubscriptionState.client_subscriptions)
async def subs_cancel_start(callback: CallbackQuery, state: FSMContext):
    sub_id = int(callback.data.rsplit("_", 1)[-1])
    await state.update_data(cancel_sub_id=sub_id)
    await state.set_state(SubscriptionState.cancel_confirm)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Да, отменить абонемент", callback_data="subs_cancel_confirm")],
        [InlineKeyboardButton(text="⬅️ Отмена", callback_data="subs_back_client")],
    ])
    await callback.message.edit_text(
        "Отменить абонемент?\n\n"
        "Все будущие записи по этому абонементу также будут отменены.\n"
        "Прошедшие занятия останутся в истории.",
        reply_markup=keyboard,
    )
    await callback.answer()


@router.callback_query(F.data == "subs_cancel_confirm", SubscriptionState.cancel_confirm)
async def subs_cancel_confirm(callback: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    sub_id = user_data.get("cancel_sub_id")
    try:
        api = BackendAPIClient()
        updated_sub = await api.subscription_update(sub_id, status="cancelled")
    except Exception as e:
        logger.exception("subscription_cancel error")
        await callback.message.edit_text(f"Ошибка: {e}")
        await callback.answer()
        return

    await callback.message.edit_text(
        "✅ Абонемент отменён.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="⬅️ К абонементам клиента", callback_data="subs_back_client")
        ]]),
    )
    await state.set_state(SubscriptionState.client_subscriptions)
    await callback.answer()


@router.callback_query(F.data == "subs_back_client")
async def subs_back_client(callback: CallbackQuery, state: FSMContext):
    await _show_subs_for_client(callback, state)
    await callback.answer()


# =====================================================================
# Внешний API для schedule.py
# =====================================================================

async def start_issue_flow_inline(
    callback: CallbackQuery,
    state: FSMContext,
    *,
    client_id: int,
    client_name: str,
    return_to: str = "create_record",
) -> None:
    await state.update_data(
        subs_client_id=client_id,
        subs_client_name=client_name,
        **{RETURN_KEY: return_to},
    )
    await subs_issue_start(callback, state)

# =====================================================================
# Передача клиента другому специалисту (admin/methodist)
# =====================================================================

@router.callback_query(F.data.startswith("subs_transfer_"), SubscriptionState.client_subscriptions)
async def subs_transfer_start(callback: CallbackQuery, state: FSMContext):
    """Начало передачи клиента: проверяем возможность и показываем список специалистов."""
    user_data = await state.get_data()
    role = user_data.get("role", "specialist")
    if role not in ("admin", "methodist"):
        await callback.answer("Недостаточно прав.", show_alert=True)
        return

    client_id = int(callback.data.rsplit("_", 1)[-1])
    client_name = user_data.get("subs_client_name") or "клиента"

    api = BackendAPIClient()

    # Проверяем, можно ли передать
    try:
        check = await api.client_can_transfer(client_id)
    except Exception as e:
        logger.exception("can_transfer error")
        await callback.message.edit_text(f"Ошибка: {e}")
        await callback.answer()
        return

    if not check.get("can_transfer"):
        await callback.message.edit_text(
            f"Передача невозможна.\n\n{check.get('reason', '')}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="⬅️ Назад", callback_data=f"subs_client_back_{client_id}")
            ]]),
        )
        await callback.answer()
        return

    # Получаем список специалистов
    try:
        users = await api.users_get_all()
    except Exception as e:
        logger.exception("users_list error")
        await callback.message.edit_text(f"Ошибка: {e}")
        await callback.answer()
        return

    current_owner_id = user_data.get("subs_client_owner_id")  # может быть не сохранён — это не критично

    candidates = [
        u for u in users
        if u.get("role") in ("specialist", "methodist", "admin")
        and not u.get("deleted_at")
        and u.get("is_active", True)
        and u.get("id") != current_owner_id
    ]

    if not candidates:
        await callback.message.edit_text(
            "Нет доступных специалистов для передачи.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="⬅️ Назад", callback_data=f"subs_client_back_{client_id}")
            ]]),
        )
        await callback.answer()
        return

    candidates.sort(key=lambda u: (u.get("name") or "").lower())
    await state.update_data(
        transfer_client_id=client_id,
        transfer_client_name=client_name,
        transfer_candidates=candidates,
    )

    buttons = []
    for i, u in enumerate(candidates):
        label = u.get("name") or u.get("phone") or f"id={u['id']}"
        role_label = {"admin": "админ", "methodist": "методист", "specialist": "специалист"}.get(
            u.get("role"), ""
        )
        if role_label:
            label = f"{label} ({role_label})"
        if len(label) > 50:
            label = label[:47] + "…"
        buttons.append([InlineKeyboardButton(
            text=label,
            callback_data=f"subs_transfer_to_{i}",
        )])
    buttons.append([InlineKeyboardButton(
        text="⬅️ Отмена", callback_data=f"subs_client_back_{client_id}",
    )])

    await callback.message.edit_text(
        f"🔁 Передать клиента «{client_name}»\n\nКому передаём?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await state.set_state(SubscriptionState.transfer_select_owner)
    await callback.answer()


@router.callback_query(F.data.startswith("subs_transfer_to_"), SubscriptionState.transfer_select_owner)
async def subs_transfer_to(callback: CallbackQuery, state: FSMContext):
    """Подтверждение и собственно передача."""
    idx = int(callback.data.rsplit("_", 1)[-1])
    user_data = await state.get_data()

    candidates = user_data.get("transfer_candidates") or []
    if idx >= len(candidates):
        await callback.answer("Специалист не найден.", show_alert=True)
        return
    new_owner = candidates[idx]
    client_id = user_data.get("transfer_client_id")
    client_name = user_data.get("transfer_client_name") or "клиент"

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
                InlineKeyboardButton(text="⬅️ К клиентам", callback_data="subscriptions_menu")
            ]]),
        )
        await callback.answer()
        return
    except Exception as e:
        logger.exception("client_transfer error")
        await callback.message.edit_text(f"Ошибка: {e}")
        await callback.answer()
        return

    new_owner_name = new_owner.get("name") or new_owner.get("phone") or "?"
    await callback.message.edit_text(
        f"✅ Клиент «{client_name}» передан специалисту «{new_owner_name}».",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="⬅️ К клиентам", callback_data="subscriptions_menu")
        ]]),
    )
    await state.set_state(SubscriptionState.main)
    await callback.answer("Передан")


@router.callback_query(F.data.startswith("subs_client_back_"))
async def subs_client_back(callback: CallbackQuery, state: FSMContext):
    """Возврат к карточке клиента из под-экрана (передача и т.д.)."""
    client_id = int(callback.data.rsplit("_", 1)[-1])
    user_data = await state.get_data()
    cache = user_data.get("subs_clients_cache") or []
    # Найти индекс этого клиента в кэше
    for i, c in enumerate(cache):
        if c.get("id") == client_id:
            # Эмулируем callback subs_client_<i>
            callback.data = f"subs_client_{i}"
            await subs_client_picked(callback, state)
            return
    # Если кэша нет — возврат к списку
    await _show_clients_list(callback, state, return_to=None)
    await callback.answer()
