"""
Раздел "👥 Группы" в боте.

Возможности:
- Список групп → детали группы → состав, ред-я, удаление
- Создание новой группы (для алгоритмики)
- Управление составом: добавить/убрать клиента
- Создание группового занятия (см. handlers/group_session.py — отдельный файл)

Доступ: см меню — пункт виден всем; реальные права на создание/редактирование
проверяются на стороне backend (поле role в API). На уровне UI кнопки доступны
всем — если не хватит прав, backend вернёт 403, мы покажем сообщение.
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
    Message,
)

from services.api_client import BackendAPIClient

router = Router()
logger = logging.getLogger(__name__)

DAY_NAMES_SHORT = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


class GroupsState(StatesGroup):
    main = State()  # список групп
    detail = State()  # детали выбранной группы

    # Создание
    create_enter_name = State()
    create_select_service = State()

    # Редактирование
    edit_enter_name = State()

    # Управление составом
    manage_participants = State()
    add_participant = State()


# =====================================================================
# Главный экран — список групп
# =====================================================================

@router.callback_query(F.data == "groups_menu")
async def groups_menu(callback: CallbackQuery, state: FSMContext):
    await _show_groups_list(callback, state)
    await callback.answer()


async def _show_groups_list(callback: CallbackQuery, state: FSMContext):
    try:
        api = BackendAPIClient()
        groups = await api.groups_list()
    except Exception as e:
        logger.exception("groups_list error")
        await callback.message.edit_text(f"Ошибка: {e}")
        return

    groups = [g for g in groups if not g.get("deleted_at")]
    groups.sort(key=lambda g: (g.get("name") or "").lower())

    await state.update_data(groups_cache=groups)

    if not groups:
        text = "👥 Группы\n\nГрупп ещё нет. Создайте первую."
    else:
        lines = ["👥 Группы\n"]
        for g in groups:
            participants = g.get("participants") or []
            active_count = sum(1 for p in participants if p.get("is_active"))
            schedule_hint = ""
            if g.get("day_of_week") is not None and g.get("time"):
                day_idx = g["day_of_week"]
                if 0 <= day_idx < 7:
                    schedule_hint = f" — {DAY_NAMES_SHORT[day_idx]} {g['time']}"
            service_label = f" [{g['service_name']}]" if g.get("service_name") else ""
            lines.append(f"• {g.get('name', '?')}{service_label} ({active_count} уч.){schedule_hint}")
        text = "\n".join(lines)

    buttons = []
    for i, g in enumerate(groups):
        label = g.get("name", "?")
        if len(label) > 50:
            label = label[:47] + "…"
        buttons.append([InlineKeyboardButton(
            text=label,
            callback_data=f"grp_pick_{i}",
        )])
    buttons.append([InlineKeyboardButton(text="➕ Создать группу", callback_data="grp_create")])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="sched_back_to_main")])

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await state.set_state(GroupsState.main)


# =====================================================================
# Детали группы
# =====================================================================

@router.callback_query(F.data.startswith("grp_pick_"), GroupsState.main)
async def grp_pick(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.rsplit("_", 1)[-1])
    user_data = await state.get_data()
    groups = user_data.get("groups_cache") or []
    if idx >= len(groups):
        await callback.answer("Группа не найдена.", show_alert=True)
        return
    group = groups[idx]
    await state.update_data(group_id=group["id"])
    await _show_group_detail(callback, state)
    await callback.answer()


async def _show_group_detail(callback: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    group_id = user_data["group_id"]

    try:
        api = BackendAPIClient()
        group = await api.group_get(group_id)
    except Exception as e:
        logger.exception("group_get error")
        await callback.message.edit_text(f"Ошибка: {e}")
        return

    name = group.get("name", "")
    max_part = group.get("max_participants", 6)
    service_name = group.get("service_name") or "—"
    participants = [p for p in (group.get("participants") or []) if p.get("is_active")]

    schedule_hint = "—"
    if group.get("day_of_week") is not None and group.get("time"):
        idx = group["day_of_week"]
        if 0 <= idx < 7:
            schedule_hint = f"{DAY_NAMES_SHORT[idx]} в {group['time']}"

    lines = [
        f"👥 Группа «{name}»",
        f"Тип: {service_name}",
        f"Расписание: {schedule_hint}",
        f"Участники: {len(participants)}/{max_part}",
        "",
    ]
    if participants:
        for p in participants:
            lines.append(f"• {p.get('client_name', '?')}")
    else:
        lines.append("Состав пуст.")

    buttons = [
        [InlineKeyboardButton(text="👤 Управлять составом", callback_data="grp_manage")],
        [InlineKeyboardButton(text="✏️ Изменить название", callback_data="grp_rename")],
        [InlineKeyboardButton(text="🗑️ Удалить группу", callback_data="grp_delete")],
        [InlineKeyboardButton(text="⬅️ К списку групп", callback_data="groups_menu")],
    ]

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await state.set_state(GroupsState.detail)


# =====================================================================
# Создание группы
# =====================================================================

@router.callback_query(F.data == "grp_create")
async def grp_create(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "Введите название группы\n(например, «Группа \"Будем танцевать\"»):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="⬅️ Отмена", callback_data="groups_menu")
        ]]),
    )
    await state.set_state(GroupsState.create_enter_name)
    await callback.answer()


@router.message(GroupsState.create_enter_name)
async def grp_create_name(message: Message, state: FSMContext):
    name = (message.text or "").strip()
    if not name:
        await message.answer("Название не может быть пустым.")
        return
    await state.update_data(new_group_name=name)

    # Выбор услуги — все групповые из справочника (Логоритмика, Чтение, …)
    try:
        api = BackendAPIClient()
        services = await api.services_list()
    except Exception as e:
        logger.exception("services_list error")
        await message.answer(f"Ошибка: {e}")
        return

    group_services = [s for s in services if s.get("is_group") and s.get("is_active")]
    if not group_services:
        await message.answer("В справочнике нет групповых услуг.")
        return

    # Если групповая услуга только одна — создаём сразу, без выбора
    if len(group_services) == 1:
        await _create_group_and_show(message, state, group_services[0]["id"])
        return

    buttons = []
    for s in group_services:
        buttons.append([InlineKeyboardButton(
            text=s["name"],
            callback_data=f"grp_create_svc_{s['id']}",
        )])
    buttons.append([InlineKeyboardButton(text="⬅️ Отмена", callback_data="groups_menu")])

    await message.answer(
        "Выберите тип группы:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await state.set_state(GroupsState.create_select_service)


@router.callback_query(F.data.startswith("grp_create_svc_"), GroupsState.create_select_service)
async def grp_create_svc(callback: CallbackQuery, state: FSMContext):
    service_id = int(callback.data.rsplit("_", 1)[-1])
    await _create_group_and_show(callback, state, service_id)
    await callback.answer()


async def _create_group_and_show(target, state: FSMContext, service_id: int):
    """
    Создаёт группу и показывает её детали.
    target — либо Message (когда пришли из text-handler), либо CallbackQuery.
    """
    user_data = await state.get_data()

    api = BackendAPIClient()
    try:
        group = await api.group_create(
            name=user_data["new_group_name"],
            service_id=service_id,
            day_of_week=None,
            time=None,
        )
    except httpx.HTTPStatusError as e:
        detail = ""
        try:
            detail = e.response.json().get("detail", "")
        except Exception:
            pass
        msg_text = f"Не удалось создать группу: {detail or e}"
        if hasattr(target, "message"):
            await target.message.edit_text(msg_text)
        else:
            await target.answer(msg_text)
        return
    except Exception as e:
        logger.exception("group_create error")
        msg_text = f"Ошибка: {e}"
        if hasattr(target, "message"):
            await target.message.edit_text(msg_text)
        else:
            await target.answer(msg_text)
        return

    await state.update_data(group_id=group["id"])

    # Показываем детали свежесозданной группы
    if hasattr(target, "message"):
        # CallbackQuery
        await target.message.edit_text(f"✅ Группа «{group['name']}» создана.")
        fake_msg = await target.message.answer("…")
    else:
        # Message
        await target.answer(f"✅ Группа «{group['name']}» создана.")
        fake_msg = await target.answer("…")

    class _C:
        def __init__(self, m): self.message = m
        async def answer(self, *a, **k): return None

    await _show_group_detail(_C(fake_msg), state)





# =====================================================================
# Переименование группы
# =====================================================================

@router.callback_query(F.data == "grp_rename", GroupsState.detail)
async def grp_rename(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "Введите новое название группы:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="⬅️ Отмена", callback_data="grp_back_detail")
        ]]),
    )
    await state.set_state(GroupsState.edit_enter_name)
    await callback.answer()


@router.message(GroupsState.edit_enter_name)
async def grp_rename_input(message: Message, state: FSMContext):
    name = (message.text or "").strip()
    if not name:
        await message.answer("Название не может быть пустым.")
        return
    user_data = await state.get_data()
    group_id = user_data["group_id"]
    try:
        api = BackendAPIClient()
        await api.group_update(group_id, name=name)
    except Exception as e:
        logger.exception("group_update error")
        await message.answer(f"Ошибка: {e}")
        return
    await message.answer("✅ Название обновлено.")
    fake_msg = await message.answer("…")

    class _C:
        def __init__(self, m): self.message = m
        async def answer(self, *a, **k): return None

    await _show_group_detail(_C(fake_msg), state)


@router.callback_query(F.data == "grp_back_detail")
async def grp_back_detail(callback: CallbackQuery, state: FSMContext):
    await _show_group_detail(callback, state)
    await callback.answer()


# =====================================================================
# Удаление группы
# =====================================================================

@router.callback_query(F.data == "grp_delete", GroupsState.detail)
async def grp_delete(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "Удалить группу?\n\n"
        "Состав группы будет очищен. Уже выданные абонементы клиентов "
        "потеряют привязку к этой группе, но сами не будут удалены.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🗑️ Да, удалить", callback_data="grp_delete_confirm")],
            [InlineKeyboardButton(text="⬅️ Отмена", callback_data="grp_back_detail")],
        ]),
    )
    await callback.answer()


@router.callback_query(F.data == "grp_delete_confirm", GroupsState.detail)
async def grp_delete_confirm(callback: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    group_id = user_data["group_id"]
    try:
        api = BackendAPIClient()
        ok = await api.group_delete(group_id)
    except Exception as e:
        logger.exception("group_delete error")
        await callback.message.edit_text(f"Ошибка: {e}")
        await callback.answer()
        return
    if not ok:
        await callback.message.edit_text("Не удалось удалить группу.")
        await callback.answer()
        return
    await callback.message.edit_text("✅ Группа удалена.")
    fake_msg = await callback.message.answer("…")

    class _C:
        def __init__(self, m): self.message = m
        async def answer(self, *a, **k): return None

    await _show_groups_list(_C(fake_msg), state)
    await callback.answer()


# =====================================================================
# Управление составом
# =====================================================================

@router.callback_query(F.data == "grp_manage", GroupsState.detail)
async def grp_manage(callback: CallbackQuery, state: FSMContext):
    await _show_manage_participants(callback, state)
    await callback.answer()


async def _show_manage_participants(callback: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    group_id = user_data["group_id"]

    try:
        api = BackendAPIClient()
        group = await api.group_get(group_id)
    except Exception as e:
        logger.exception("group_get error")
        await callback.message.edit_text(f"Ошибка: {e}")
        return

    participants = [p for p in (group.get("participants") or []) if p.get("is_active")]
    name = group.get("name", "")
    max_part = group.get("max_participants", 6)

    text_lines = [f"👥 Состав группы «{name}» ({len(participants)}/{max_part})", ""]

    buttons = []
    if participants:
        for p in participants:
            label = f"❌ {p.get('client_name', '?')}"
            if len(label) > 50:
                label = label[:47] + "…"
            buttons.append([InlineKeyboardButton(
                text=label,
                callback_data=f"grp_remove_{p['client_id']}",
            )])
    else:
        text_lines.append("В составе пусто.")

    buttons.append([InlineKeyboardButton(
        text="➕ Добавить клиента",
        callback_data="grp_add_participant",
    )])
    buttons.append([InlineKeyboardButton(text="⬅️ К группе", callback_data="grp_back_detail")])

    await callback.message.edit_text(
        "\n".join(text_lines) + "\n\nНажмите ❌ чтобы исключить из группы.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await state.set_state(GroupsState.manage_participants)


@router.callback_query(F.data.startswith("grp_remove_"), GroupsState.manage_participants)
async def grp_remove_participant(callback: CallbackQuery, state: FSMContext):
    client_id = int(callback.data.rsplit("_", 1)[-1])
    user_data = await state.get_data()
    group_id = user_data["group_id"]
    try:
        api = BackendAPIClient()
        await api.group_remove_participant(group_id, client_id)
    except Exception as e:
        logger.exception("group_remove_participant error")
        await callback.message.edit_text(f"Ошибка: {e}")
        await callback.answer()
        return
    await _show_manage_participants(callback, state)
    await callback.answer("Удалён из группы")


@router.callback_query(F.data == "grp_add_participant", GroupsState.manage_participants)
async def grp_add_participant_start(callback: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    specialist_id = user_data.get("global_user_id")
    group_id = user_data["group_id"]

    try:
        api = BackendAPIClient()
        clients = await api.clients_get_all(user_id=specialist_id)
        group = await api.group_get(group_id)
    except Exception as e:
        logger.exception("clients/group fetch error")
        await callback.message.edit_text(f"Ошибка: {e}")
        await callback.answer()
        return

    clients = [c for c in clients if not c.get("deleted_at")]
    existing_ids = {
        p["client_id"] for p in (group.get("participants") or []) if p.get("is_active")
    }
    available = [c for c in clients if c["id"] not in existing_ids]
    available.sort(key=lambda c: (c.get("name") or "").lower())

    if not available:
        await callback.message.edit_text(
            "Нет клиентов, которых можно добавить в группу.\n"
            "Все ваши клиенты уже в составе.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="⬅️ Назад", callback_data="grp_manage")
            ]]),
        )
        await callback.answer()
        return

    await state.update_data(add_part_clients_cache=available)

    buttons = []
    for i, c in enumerate(available):
        label = c.get("name", "?")
        if len(label) > 50:
            label = label[:47] + "…"
        buttons.append([InlineKeyboardButton(
            text=label,
            callback_data=f"grp_add_pick_{i}",
        )])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="grp_manage")])

    await callback.message.edit_text(
        "Выберите клиента для добавления в группу:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await state.set_state(GroupsState.add_participant)
    await callback.answer()


@router.callback_query(F.data.startswith("grp_add_pick_"), GroupsState.add_participant)
async def grp_add_pick(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.rsplit("_", 1)[-1])
    user_data = await state.get_data()
    available = user_data.get("add_part_clients_cache") or []
    if idx >= len(available):
        await callback.answer("Клиент не найден.", show_alert=True)
        return
    client = available[idx]
    group_id = user_data["group_id"]
    try:
        api = BackendAPIClient()
        await api.group_add_participant(group_id, client["id"])
    except Exception as e:
        logger.exception("group_add_participant error")
        await callback.message.edit_text(f"Ошибка: {e}")
        await callback.answer()
        return
    await _show_manage_participants(callback, state)
    await callback.answer(f"Добавлен: {client.get('name', '')}")