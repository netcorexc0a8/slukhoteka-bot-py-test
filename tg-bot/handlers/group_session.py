"""
Создание группового занятия (алгоритмика).

Поток:
  «📅 Расписание» → «➕ Создать групповое занятие»
    → выбор группы
    → выбор даты
    → выбор времени
    → отметка пришедших клиентов галочками (по умолчанию все активные участники)
    → опциональный шаг — выбор со-ведущих (основной = текущий пользователь)
    → создаётся N броней, по одной на каждого отмеченного клиента

Логика проверок (на стороне backend):
  - Каждая бронь должна быть привязана к абонементу клиента (logorhythmics).
  - Если у клиента нет активного абонемента «Алгоритмика» с привязкой к этой
    группе — бот покажет это в списке отметки и не даст пометить участника.
  - Weekly limit (раз в неделю) — backend проверит при создании.
"""
import asyncio
import logging
from datetime import datetime, timedelta

import httpx
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from config import settings
from keyboards.calendar import get_calendar_keyboard
from services.api_client import BackendAPIClient

router = Router()
logger = logging.getLogger(__name__)

DAY_NAMES = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]


def _format_date_human(date_str: str) -> str:
    d = datetime.strptime(date_str, "%Y-%m-%d")
    return f"{d.strftime('%d.%m.%Y')} ({DAY_NAMES[d.weekday()]})"


class GroupSessionState(StatesGroup):
    select_group = State()
    select_date = State()
    select_time = State()
    pick_attendees = State()
    select_co_specialists = State()


# =====================================================================
# Шаг 1: выбор группы
# =====================================================================

@router.callback_query(F.data == "schedule_create_group")
async def gs_start(callback: CallbackQuery, state: FSMContext):
    try:
        api = BackendAPIClient()
        groups = await api.groups_list()
    except Exception as e:
        logger.exception("groups_list error")
        await callback.message.edit_text(f"Ошибка: {e}")
        await callback.answer()
        return

    groups = [g for g in groups if not g.get("deleted_at") and g.get("is_active", True)]
    groups.sort(key=lambda g: (g.get("name") or "").lower())

    if not groups:
        await callback.message.edit_text(
            "Нет активных групп. Создайте группу в разделе «👥 Группы».",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="⬅️ Назад", callback_data="sched_back_to_main")
            ]]),
        )
        await callback.answer()
        return

    await state.update_data(gs_groups_cache=groups)

    buttons = []
    for i, g in enumerate(groups):
        active_count = sum(1 for p in (g.get("participants") or []) if p.get("is_active"))
        label = f"{g.get('name', '?')} ({active_count} уч.)"
        if len(label) > 50:
            label = label[:47] + "…"
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"gs_pick_grp_{i}")])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="sched_back_to_main")])

    await callback.message.edit_text(
        "Выберите группу:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await state.set_state(GroupSessionState.select_group)
    await callback.answer()


@router.callback_query(F.data.startswith("gs_pick_grp_"), GroupSessionState.select_group)
async def gs_group_picked(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.rsplit("_", 1)[-1])
    user_data = await state.get_data()
    groups = user_data.get("gs_groups_cache") or []
    if idx >= len(groups):
        await callback.answer("Группа не найдена.", show_alert=True)
        return
    group = groups[idx]
    await state.update_data(gs_group_id=group["id"], gs_group_name=group["name"])

    today = datetime.now()
    await state.update_data(calendar_year=today.year, calendar_month=today.month)
    await callback.message.edit_text(
        f"Группа: «{group['name']}»\nВыберите дату занятия:",
        reply_markup=get_calendar_keyboard(today.year, today.month, []),
    )
    await state.set_state(GroupSessionState.select_date)
    await callback.answer()


# =====================================================================
# Шаг 2: дата (через общий calendar_callback в schedule.py)
# Шаг 3: выбор времени
# =====================================================================

async def gs_show_time_slots(callback: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    date_str = user_data["gs_date"]
    specialist_id = user_data.get("global_user_id")

    try:
        # For group sessions, don't check specialist availability as it should allow multiple concurrent group bookings
        busy = set()

        slots = []
        for hour in range(settings.START_HOUR, settings.END_HOUR + 1):
            time_str = f"{hour:02d}:00"
            if time_str not in busy:
                slots.append(time_str)

        if not slots:
            await callback.message.edit_text(
                f"На {_format_date_human(date_str)} нет свободных слотов.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text="⬅️ Назад к дате", callback_data="gs_back_to_date")
                ]]),
            )
            return

        rows, row = [], []
        for i, t in enumerate(slots):
            row.append(InlineKeyboardButton(text=t, callback_data=f"gs_pick_time_{t}"))
            if len(row) == 4 or i == len(slots) - 1:
                rows.append(row)
                row = []
        rows.append([InlineKeyboardButton(text="⬅️ Назад к дате", callback_data="gs_back_to_date")])

        await callback.message.edit_text(
            f"Группа: «{user_data.get('gs_group_name', '')}»\n"
            f"Дата: {_format_date_human(date_str)}\n\n"
            f"Выберите время:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
        )
        await state.set_state(GroupSessionState.select_time)
    except Exception as e:
        logger.exception("gs time slots error")
        await callback.message.edit_text(f"Ошибка: {e}")


@router.callback_query(F.data == "gs_back_to_date", GroupSessionState.select_time)
async def gs_back_to_date(callback: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    year = user_data.get("calendar_year", datetime.now().year)
    month = user_data.get("calendar_month", datetime.now().month)
    await callback.message.edit_text(
        f"Группа: «{user_data.get('gs_group_name', '')}»\nВыберите дату занятия:",
        reply_markup=get_calendar_keyboard(year, month, []),
    )
    await state.set_state(GroupSessionState.select_date)
    await callback.answer()


# =====================================================================
# Шаг 4: отметка пришедших (галочки)
# =====================================================================

@router.callback_query(F.data.startswith("gs_pick_time_"), GroupSessionState.select_time)
async def gs_time_picked(callback: CallbackQuery, state: FSMContext):
    time_str = callback.data.rsplit("_", 1)[-1]
    await state.update_data(gs_time=time_str)
    await _show_attendees(callback, state, init=True)
    await callback.answer()


async def _show_attendees(callback: CallbackQuery, state: FSMContext, init: bool = False):
    """
    Показываем список участников группы с галочками.
    Для каждого ищем активный абонемент Алгоритмика, привязанный к этой группе.
    Если абонемента нет — клиент показан как недоступный.
    """
    user_data = await state.get_data()
    group_id = user_data["gs_group_id"]
    api = BackendAPIClient()

    try:
        group = await api.group_get(group_id)
    except Exception as e:
        logger.exception("group_get error")
        await callback.message.edit_text(f"Ошибка: {e}")
        return

    participants = [p for p in (group.get("participants") or []) if p.get("is_active")]

    # Собираем для каждого участника подходящий абонемент
    enriched = []
    for p in participants:
        client_id = p["client_id"]
        try:
            subs = await api.subscriptions_for_client(client_id=client_id, only_usable=True)
        except Exception:
            subs = []
        # Берём первый usable абонемент алгоритмики этой группы
        match = next(
            (s for s in subs
             if s.get("group_id") == group_id and s.get("service_type") == "logorhythmics"),
            None,
        )
        enriched.append({
            "client_id": client_id,
            "client_name": p.get("client_name", "?"),
            "subscription_id": match["id"] if match else None,
            "remaining": (match.get("remaining_sessions") if match else 0) or 0,
            "total": (match.get("total_sessions") if match else 0) or 0,
        })

    await state.update_data(gs_enriched=enriched)

    # Инициализируем галочки: по умолчанию все, у кого есть активный абонемент
    if init:
        selected = {e["client_id"] for e in enriched if e["subscription_id"] is not None}
        await state.update_data(gs_selected=list(selected))
        user_data = await state.get_data()

    selected_set = set(user_data.get("gs_selected", []))

    lines = [
        f"👥 «{user_data.get('gs_group_name', '')}»",
        f"📅 {_format_date_human(user_data['gs_date'])} в {user_data['gs_time']}",
        "",
        "Отметьте кто пришёл:",
    ]

    buttons = []
    for e in enriched:
        cid = e["client_id"]
        # Без абонемента — нельзя записать
        if e["subscription_id"] is None:
            label = f"⛔ {e['client_name']} (нет абонемента)"
        else:
            mark = "✅" if cid in selected_set else "⬜"
            label = f"{mark} {e['client_name']} ({e['remaining']}/{e['total']})"
        if len(label) > 60:
            label = label[:57] + "…"
        # Если без абонемента — кнопка-заглушка
        cb = f"gs_toggle_{cid}" if e["subscription_id"] is not None else "gs_noop"
        buttons.append([InlineKeyboardButton(text=label, callback_data=cb)])

    if any(e["subscription_id"] is not None for e in enriched):
        buttons.append([
            InlineKeyboardButton(text="➡️ Далее: ведущие", callback_data="gs_to_co_specs"),
        ])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад ко времени", callback_data="gs_back_to_time")])

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await state.set_state(GroupSessionState.pick_attendees)


@router.callback_query(F.data == "gs_noop", GroupSessionState.pick_attendees)
async def gs_noop(callback: CallbackQuery, state: FSMContext):
    await callback.answer(
        "У клиента нет активного абонемента «Алгоритмика» в этой группе. "
        "Выдайте ему абонемент в разделе «🎫 Абонементы».",
        show_alert=True,
    )


@router.callback_query(F.data.startswith("gs_toggle_"), GroupSessionState.pick_attendees)
async def gs_toggle(callback: CallbackQuery, state: FSMContext):
    client_id = int(callback.data.rsplit("_", 1)[-1])
    user_data = await state.get_data()
    selected = set(user_data.get("gs_selected", []))
    if client_id in selected:
        selected.discard(client_id)
    else:
        selected.add(client_id)
    await state.update_data(gs_selected=list(selected))
    await _show_attendees(callback, state, init=False)
    await callback.answer()


@router.callback_query(F.data == "gs_back_to_time", GroupSessionState.pick_attendees)
async def gs_back_to_time(callback: CallbackQuery, state: FSMContext):
    await gs_show_time_slots(callback, state)
    await callback.answer()


# =====================================================================
# Шаг 5: выбор со-ведущих (опционально)
# =====================================================================

@router.callback_query(F.data == "gs_to_co_specs", GroupSessionState.pick_attendees)
async def gs_to_co_specs(callback: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    selected = user_data.get("gs_selected", [])
    if not selected:
        await callback.answer("Отметьте хотя бы одного клиента.", show_alert=True)
        return
    await _show_co_specs(callback, state, init=True)
    await callback.answer()


async def _show_co_specs(callback: CallbackQuery, state: FSMContext, init: bool = False):
    user_data = await state.get_data()
    api = BackendAPIClient()
    try:
        users_resp = await api.users_get_all(limit=200)
        users = users_resp if isinstance(users_resp, list) else users_resp.get("users", [])
    except Exception as e:
        logger.exception("users_get_all error")
        await callback.message.edit_text(f"Ошибка: {e}")
        return

    # Только специалисты/методисты/админы могут быть ведущими — все остальные не подходят
    leaders = [u for u in users if u.get("role") in ("specialist", "methodist", "admin")]
    me_id = user_data.get("global_user_id")
    # Исключаем самого себя из списка кандидатов в со-ведущие — он уже основной
    leaders = [u for u in leaders if u["id"] != me_id]
    leaders.sort(key=lambda u: (u.get("name") or u.get("phone") or "").lower())

    if init:
        await state.update_data(gs_co_specs=[])
        user_data = await state.get_data()

    selected_co = set(user_data.get("gs_co_specs", []))

    lines = [
        f"👥 «{user_data.get('gs_group_name', '')}»",
        f"📅 {_format_date_human(user_data['gs_date'])} в {user_data['gs_time']}",
        f"Участников: {len(user_data.get('gs_selected', []))}",
        "",
        "Основной ведущий: вы",
        "Отметьте со-ведущих (опционально):",
    ]

    buttons = []
    for u in leaders:
        uid = u["id"]
        mark = "✅" if uid in selected_co else "⬜"
        label = f"{mark} {u.get('name') or u.get('phone') or '?'}"
        if len(label) > 60:
            label = label[:57] + "…"
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"gs_co_toggle_{uid}")])

    buttons.append([InlineKeyboardButton(text="✅ Создать занятие", callback_data="gs_create")])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="gs_back_to_attendees")])

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await state.set_state(GroupSessionState.select_co_specialists)


@router.callback_query(F.data.startswith("gs_co_toggle_"), GroupSessionState.select_co_specialists)
async def gs_co_toggle(callback: CallbackQuery, state: FSMContext):
    uid = int(callback.data.rsplit("_", 1)[-1])
    user_data = await state.get_data()
    selected_co = set(user_data.get("gs_co_specs", []))
    if uid in selected_co:
        selected_co.discard(uid)
    else:
        selected_co.add(uid)
    await state.update_data(gs_co_specs=list(selected_co))
    await _show_co_specs(callback, state, init=False)
    await callback.answer()


@router.callback_query(F.data == "gs_back_to_attendees", GroupSessionState.select_co_specialists)
async def gs_back_to_attendees(callback: CallbackQuery, state: FSMContext):
    await _show_attendees(callback, state, init=False)
    await callback.answer()


# =====================================================================
# Шаг 6: создание броней
# =====================================================================

@router.callback_query(F.data == "gs_create", GroupSessionState.select_co_specialists)
async def gs_create(callback: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    me_id = user_data.get("global_user_id")
    selected = set(user_data.get("gs_selected", []))
    co_specs = user_data.get("gs_co_specs", [])
    enriched = user_data.get("gs_enriched") or []
    date_str = user_data["gs_date"]
    time_str = user_data["gs_time"]

    # Полный список ведущих этого занятия — основной + co_specs
    co_specialist_ids = list({me_id, *co_specs})

    start_time = f"{date_str}T{time_str}:00"
    end_dt = datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%S") + timedelta(hours=1)
    end_time = end_dt.strftime("%Y-%m-%dT%H:%M:%S")

    api = BackendAPIClient()
    created = []
    created_subs: list[dict] = []  # для последующего предложения серии
    failed = []  # [(client_name, error_text)]

    # Создаём по одной брони на каждого выбранного клиента
    tasks = []
    task_clients = []
    task_sub_ids = []
    for e in enriched:
        if e["client_id"] not in selected:
            continue
        if e["subscription_id"] is None:
            failed.append((e["client_name"], "нет абонемента"))
            continue
        task = api.booking_create(
            subscription_id=e["subscription_id"],
            start_time=start_time,
            end_time=end_time,
            specialist_id=me_id,
            co_specialist_ids=co_specialist_ids,
        )
        tasks.append(task)
        task_clients.append(e["client_name"])
        task_sub_ids.append(e["subscription_id"])

    # Execute all bookings concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for name, sub_id, result in zip(task_clients, task_sub_ids, results):
        if isinstance(result, Exception):
            if isinstance(result, httpx.HTTPStatusError):
                detail = ""
                try:
                    detail = result.response.json().get("detail", "")
                except Exception:
                    pass
                failed.append((name, detail or str(result)))
            else:
                logger.exception("booking_create (group) error")
                failed.append((name, str(result)))
        else:
            created.append(name)
            # Запомним subscription и оставшийся остаток после этой брони
            remaining = (result.get("subscription_remaining") or 0)
            created_subs.append({
                "client_name": name,
                "subscription_id": sub_id,
                "booking_id": result.get("id"),
                "remaining_after": remaining,
            })

    lines = [
        "✅ Занятие создано." if created else "⚠️ Ничего не создано.",
        f"📅 {_format_date_human(date_str)} в {time_str}",
        f"👥 «{user_data.get('gs_group_name', '')}»",
        "",
    ]
    if created:
        lines.append(f"Записаны ({len(created)}):")
        for name in created:
            lines.append(f"  • {name}")
    if failed:
        lines.append("")
        lines.append(f"Не удалось ({len(failed)}):")
        for name, err in failed:
            short_err = err.replace("\n", " ")
            if len(short_err) > 80:
                short_err = short_err[:77] + "…"
            lines.append(f"  • {name}: {short_err}")

    # Сколько участников могут продолжить серию (есть ещё занятия)
    can_continue = [s for s in created_subs if s["remaining_after"] >= 1]

    buttons = []
    if can_continue:
        # Сохраняем данные серии в state — задействуем при подтверждении
        await state.update_data(
            gs_recurring_subs=can_continue,
            gs_recurring_first_start=start_time,
            gs_recurring_co_specialist_ids=co_specialist_ids,
        )
        # Минимальный остаток среди участников = реальное число будущих занятий в серии
        min_remaining = min(s["remaining_after"] for s in can_continue)
        buttons.append([InlineKeyboardButton(
            text=f"🔁 Создать серию для {len(can_continue)} участников (+{min_remaining} занятий)",
            callback_data="gs_recurring_yes",
        )])
    buttons.append([InlineKeyboardButton(text="⬅️ В меню расписания", callback_data="sched_back_to_main")])

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await state.set_state(None)
    await callback.answer("Готово")


@router.callback_query(F.data == "gs_recurring_yes")
async def gs_recurring_yes(callback: CallbackQuery, state: FSMContext):
    """
    Создаёт серию для всех участников, у кого остались занятия.
    Удаляем уже созданную единичную бронь у каждого, потом — recurring.
    """
    user_data = await state.get_data()
    subs_info = user_data.get("gs_recurring_subs") or []
    first_start = user_data.get("gs_recurring_first_start")
    co_specialist_ids = user_data.get("gs_recurring_co_specialist_ids") or []
    me_id = user_data.get("global_user_id")

    if not subs_info or not first_start:
        await callback.answer("Не хватает данных для серии.", show_alert=True)
        return

    api = BackendAPIClient()
    series_ok = []
    series_fail = []  # [(client_name, reason)]

    for s in subs_info:
        try:
            await api.booking_delete(booking_id=s["booking_id"], actor_id=me_id)
        except Exception as exc:
            logger.exception("booking_delete (pre-recurring group) error")
            series_fail.append((s["client_name"], f"подготовка: {exc}"))
            continue
        try:
            result = await api.booking_create_recurring(
                subscription_id=s["subscription_id"],
                first_start_time=first_start,
                specialist_id=me_id,
                co_specialist_ids=co_specialist_ids,
            )
        except httpx.HTTPStatusError as exc:
            detail = ""
            try:
                detail = exc.response.json().get("detail", "")
            except Exception:
                pass
            series_fail.append((s["client_name"], detail or str(exc)))
            continue
        except Exception as exc:
            logger.exception("booking_create_recurring (group) error")
            series_fail.append((s["client_name"], str(exc)))
            continue
        n_created = len(result.get("created", []))
        series_ok.append((s["client_name"], n_created))

    lines = ["✅ Серия создана." if series_ok else "⚠️ Серия не создана.", ""]
    if series_ok:
        for name, n in series_ok:
            lines.append(f"  • {name}: {n} занятий")
    if series_fail:
        lines.append("")
        lines.append(f"Не удалось ({len(series_fail)}):")
        for name, err in series_fail:
            short = (err or "").replace("\n", " ")
            if len(short) > 80:
                short = short[:77] + "…"
            lines.append(f"  • {name}: {short}")

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="⬅️ В меню расписания", callback_data="sched_back_to_main")
        ]]),
    )
    await callback.answer()