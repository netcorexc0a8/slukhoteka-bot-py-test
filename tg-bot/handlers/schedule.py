"""
Управление расписанием и записями (bookings).

Главное меню расписания:
  📋 Посмотреть расписание
  ➕ Создать запись           — индивидуальная (handlers/schedule.py)
  👥 Создать групповое занятие — алгоритмика (handlers/group_session.py)
  🗑️ Удалить запись
  🎫 Абонементы               — handlers/subscriptions.py
  👥 Группы                   — handlers/groups.py
"""
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
    Message,
)

from config import settings
from keyboards.calendar import get_calendar_keyboard
from services.api_client import BackendAPIClient

router = Router()
logger = logging.getLogger(__name__)


# =====================================================================
# Helpers
# =====================================================================

DAY_NAMES = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]


def _format_date_human(date_str: str) -> str:
    d = datetime.strptime(date_str, "%Y-%m-%d")
    return f"{d.strftime('%d.%m.%Y')} ({DAY_NAMES[d.weekday()]})"


def _service_short_label(service_type: str) -> str:
    return {
        "diagnostics": "Диагностика",
        "subscription_1": "Абонемент 1",
        "subscription_4": "Абонемент 4",
        "subscription_8": "Абонемент 8",
        "logorhythmics": "Алгоритмика",
    }.get(service_type, service_type)


async def _busy_dates_for_month(year: int, month: int, specialist_id=None) -> list:
    try:
        api = BackendAPIClient()
        first_day = datetime(year, month, 1)
        if month == 12:
            last_day = datetime(year + 1, 1, 1)
        else:
            last_day = datetime(year, month + 1, 1)
        bookings = await api.bookings_for_range(
            start_date=first_day.strftime("%Y-%m-%d"),
            end_date=(last_day - timedelta(days=1)).strftime("%Y-%m-%d"),
            specialist_id=specialist_id,
        )
        return list({b["start_time"][:10] for b in bookings})
    except Exception as e:
        logger.error(f"_busy_dates_for_month error: {e}")
        return []


async def _show_calendar(
    callback: CallbackQuery, state: FSMContext, prompt: str, year: int, month: int
):
    user_data = await state.get_data()
    specialist_id = user_data.get("global_user_id")
    role = user_data.get("role", "specialist")
    busy = await _busy_dates_for_month(
        year, month, specialist_id if role == "specialist" else None
    )
    calendar_kb = get_calendar_keyboard(year, month, busy)
    await callback.message.edit_text(prompt, reply_markup=calendar_kb)


# =====================================================================
# FSM
# =====================================================================

class ScheduleState(StatesGroup):
    main = State()

    view_select_date = State()
    viewing = State()

    create_select_client = State()
    create_new_client_name = State()
    create_new_client_phone = State()
    create_select_subscription = State()
    create_select_date = State()
    create_select_time = State()

    delete_select_date = State()
    delete_select_booking = State()
    delete_confirm = State()


# =====================================================================
# Главное меню "Расписание"
# =====================================================================

@router.message(F.text == "📅 Расписание")
async def cmd_schedule(message: Message, state: FSMContext):
    buttons = [
        [InlineKeyboardButton(text="📋 Посмотреть расписание", callback_data="schedule_view")],
        [InlineKeyboardButton(text="➕ Создать занятие", callback_data="schedule_create")],
        [InlineKeyboardButton(text="➕ Создать групповое занятие", callback_data="schedule_create_group")],
        [InlineKeyboardButton(text="🗑️ Удалить запись", callback_data="schedule_delete")],
        [InlineKeyboardButton(text="🎫 Абонементы", callback_data="subscriptions_menu")],
        [InlineKeyboardButton(text="👥 Группы", callback_data="groups_menu")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="schedule_back")],
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("📅 Управление расписанием", reply_markup=keyboard)
    await state.set_state(ScheduleState.main)


@router.callback_query(F.data == "schedule_back")
async def schedule_back(callback: CallbackQuery, state: FSMContext):
    from handlers.menu import show_main_menu
    await callback.message.delete()
    await show_main_menu(callback.message, state)
    await callback.answer()


# =====================================================================
# Просмотр расписания
# =====================================================================

@router.callback_query(F.data == "schedule_view")
async def schedule_view_start(callback: CallbackQuery, state: FSMContext):
    today = datetime.now()
    await state.update_data(calendar_year=today.year, calendar_month=today.month)
    await _show_calendar(callback, state, "Выберите дату для просмотра:", today.year, today.month)
    await state.set_state(ScheduleState.view_select_date)
    await callback.answer()


async def schedule_view_date(callback: CallbackQuery, state: FSMContext, date_str: str):
    user_data = await state.get_data()
    specialist_id = user_data.get("global_user_id")
    role = user_data.get("role", "specialist")

    try:
        api = BackendAPIClient()
        bookings = await api.bookings_for_date(
            date=date_str,
            specialist_id=specialist_id if role == "specialist" else None,
        )
        bookings = [b for b in bookings if not b.get("deleted_at")]
        bookings.sort(key=lambda b: b["start_time"])

        title = f"📅 Записи на {_format_date_human(date_str)}:"
        if not bookings:
            await callback.message.edit_text(
                f"{title}\n\nНет записей",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text="⬅️ Назад", callback_data="schedule_view")
                ]]),
            )
            await state.set_state(ScheduleState.viewing)
            return

        # Группируем брони по start_time + group_id, чтобы групповые занятия
        # отображались одной строкой "10:00 — Группа Среда (3 чел.)"
        groups_buckets = {}
        individuals = []
        for b in bookings:
            if b.get("booking_type") == "group" and b.get("group_id"):
                key = (b["start_time"], b["group_id"])
                groups_buckets.setdefault(key, []).append(b)
            else:
                individuals.append(b)

        lines = [title, ""]

        # Сначала индивидуальные
        for b in individuals:
            time_str = b["start_time"][11:16]
            client_name = b.get("client_name") or "—"
            spec_name = b.get("specialist_name") or ""
            service = b.get("service_name") or ""
            session_info = ""
            if b.get("subscription_total"):
                session_info = f" [{b.get('subscription_used') or 0}/{b['subscription_total']}]"

            line = f"• {time_str} — {client_name}"
            if role != "specialist" and spec_name:
                line += f" ({spec_name})"
            if service:
                line += f" — {service}{session_info}"
            lines.append(line)

        # Затем групповые
        for (start_time, _gid), items in groups_buckets.items():
            time_str = start_time[11:16]
            sample = items[0]
            group_name = sample.get("group_name") or "Группа"
            count = len(items)
            spec_name = sample.get("specialist_name") or ""
            line = f"• {time_str} — {group_name} ({count} чел.)"
            if role != "specialist" and spec_name:
                line += f" — вёл {spec_name}"
            lines.append(line)

        keyboard = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="⬅️ Назад", callback_data="schedule_view")
        ]])
        await callback.message.edit_text("\n".join(lines), reply_markup=keyboard)
        await state.set_state(ScheduleState.viewing)

    except Exception as e:
        logger.exception("schedule_view_date error")
        await callback.message.edit_text(
            f"Ошибка загрузки расписания: {e}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="⬅️ Назад", callback_data="schedule_view")
            ]]),
        )


# =====================================================================
# СОЗДАНИЕ ИНДИВИДУАЛЬНОЙ ЗАПИСИ
# =====================================================================

@router.callback_query(F.data == "schedule_create")
async def schedule_create_start(callback: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    specialist_id = user_data.get("global_user_id")

    try:
        api = BackendAPIClient()
        clients = await api.clients_get_all(user_id=specialist_id)
    except Exception as e:
        logger.exception("clients fetch error")
        await callback.message.edit_text(f"Ошибка загрузки клиентов: {e}")
        await callback.answer()
        return

    clients = [c for c in clients if not c.get("deleted_at")]
    clients.sort(key=lambda c: (c.get("name") or "").lower())

    await state.update_data(create_clients_cache=clients)

    buttons = []
    for i, c in enumerate(clients):
        label = c.get("name", "Без имени")
        if len(label) > 50:
            label = label[:47] + "…"
        buttons.append([InlineKeyboardButton(
            text=label,
            callback_data=f"sched_create_client_{i}",
        )])
    buttons.append([InlineKeyboardButton(text="➕ Новый клиент", callback_data="sched_create_new_client")])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="sched_back_to_main")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    msg = "Выберите клиента:"
    if not clients:
        msg = "У вас пока нет клиентов. Создайте первого:"
    await callback.message.edit_text(msg, reply_markup=keyboard)
    await state.set_state(ScheduleState.create_select_client)
    await callback.answer()


@router.callback_query(F.data == "sched_back_to_main")
async def sched_back_to_main(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await cmd_schedule(callback.message, state)
    await callback.answer()


@router.callback_query(F.data.startswith("sched_create_client_"), ScheduleState.create_select_client)
async def schedule_create_client_picked(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.rsplit("_", 1)[-1])
    user_data = await state.get_data()
    clients = user_data.get("create_clients_cache") or []
    if idx >= len(clients):
        await callback.answer("Клиент не найден, попробуйте снова.", show_alert=True)
        return
    client = clients[idx]
    await state.update_data(
        create_client_id=client["id"],
        create_client_name=client["name"],
    )
    await _show_subscriptions_for_create(callback, state)
    await callback.answer()


@router.callback_query(F.data == "sched_create_new_client", ScheduleState.create_select_client)
async def schedule_create_new_client(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "Введите имя нового клиента:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="⬅️ Отмена", callback_data="schedule_create")
        ]]),
    )
    await state.set_state(ScheduleState.create_new_client_name)
    await callback.answer()


@router.message(ScheduleState.create_new_client_name)
async def schedule_create_new_client_name(message: Message, state: FSMContext):
    name = (message.text or "").strip()
    if not name:
        await message.answer("Имя не может быть пустым. Введите имя:")
        return
    await state.update_data(new_client_name=name)
    await message.answer(
        "Введите телефон клиента (например, +79991234567).\n"
        "Если телефона нет — отправьте «-».",
    )
    await state.set_state(ScheduleState.create_new_client_phone)


@router.message(ScheduleState.create_new_client_phone)
async def schedule_create_new_client_phone(message: Message, state: FSMContext):
    phone_raw = (message.text or "").strip()
    user_data = await state.get_data()
    name = user_data.get("new_client_name", "Без имени")
    specialist_id = user_data.get("global_user_id")

    if phone_raw == "-" or not phone_raw:
        phone = f"manual:{specialist_id}:{int(datetime.now().timestamp())}"
    else:
        phone = phone_raw

    try:
        api = BackendAPIClient()
        client = await api.client_create(user_id=specialist_id, name=name, phone=phone)
    except httpx.HTTPStatusError as e:
        detail = ""
        try:
            detail = e.response.json().get("detail", "")
        except Exception:
            pass
        await message.answer(f"Не удалось создать клиента: {detail or e}")
        return
    except Exception as e:
        logger.exception("client_create error")
        await message.answer(f"Ошибка: {e}")
        return

    await state.update_data(
        create_client_id=client["id"],
        create_client_name=client["name"],
    )
    await message.answer(f"✅ Клиент «{client['name']}» добавлен.")

    fake_msg = await message.answer("…")
    fake_cb = _FakeCallback(message=fake_msg)
    await _show_subscriptions_for_create(fake_cb, state)


class _FakeCallback:
    def __init__(self, message: Message):
        self.message = message

    async def answer(self, *args, **kwargs):
        return None


async def _show_subscriptions_for_create(callback, state: FSMContext):
    user_data = await state.get_data()
    client_id = user_data.get("create_client_id")
    client_name = user_data.get("create_client_name", "")
    specialist_id = user_data.get("global_user_id")

    try:
        api = BackendAPIClient()
        subs = await api.subscriptions_for_client(client_id=client_id, only_usable=True)
        # На индивидуальном flow показываем только индивидуальные (без group_id)
        subs = [s for s in subs if s.get("group_id") is None]
        # Специалист — только свои; admin/methodist видят всё
        subs = [s for s in subs
                if s.get("assigned_specialist_id") in (None, specialist_id)
                or user_data.get("role") in ("admin", "methodist")]
    except Exception as e:
        logger.exception("subscriptions fetch error")
        await callback.message.edit_text(f"Ошибка загрузки абонементов: {e}")
        return

    buttons = []
    for s in subs:
        remaining = s.get("remaining_sessions", 0)
        total = s.get("total_sessions", 0)
        service_name = s.get("service_name") or _service_short_label(s.get("service_type", ""))
        label = f"{service_name} — {remaining}/{total}"
        if len(label) > 50:
            label = label[:47] + "…"
        buttons.append([InlineKeyboardButton(
            text=label,
            callback_data=f"sched_create_sub_{s['id']}",
        )])
    buttons.append([InlineKeyboardButton(
        text="🎫 Выдать новый абонемент",
        callback_data="sched_create_issue_sub",
    )])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="schedule_create")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    if subs:
        text = f"Активные индивидуальные абонементы клиента «{client_name}»:"
    else:
        text = f"У клиента «{client_name}» нет активных индивидуальных абонементов.\nВыдать новый?"

    await callback.message.edit_text(text, reply_markup=keyboard)
    await state.set_state(ScheduleState.create_select_subscription)


@router.callback_query(F.data.startswith("sched_create_sub_"), ScheduleState.create_select_subscription)
async def schedule_create_sub_picked(callback: CallbackQuery, state: FSMContext):
    sub_id = int(callback.data.rsplit("_", 1)[-1])
    await state.update_data(create_subscription_id=sub_id)

    today = datetime.now()
    await state.update_data(calendar_year=today.year, calendar_month=today.month)
    await _show_calendar(callback, state, "Выберите дату:", today.year, today.month)
    await state.set_state(ScheduleState.create_select_date)
    await callback.answer()


@router.callback_query(F.data == "sched_create_issue_sub", ScheduleState.create_select_subscription)
async def schedule_create_issue_sub(callback: CallbackQuery, state: FSMContext):
    from handlers.subscriptions import start_issue_flow_inline
    user_data = await state.get_data()
    await start_issue_flow_inline(
        callback,
        state,
        client_id=user_data["create_client_id"],
        client_name=user_data.get("create_client_name", ""),
        return_to="create_record",
    )
    await callback.answer()


async def _show_time_slots(callback: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    date_str = user_data.get("create_date")
    specialist_id = user_data.get("global_user_id")

    try:
        api = BackendAPIClient()
        bookings = await api.bookings_for_date(date=date_str, specialist_id=specialist_id)
        busy = {b["start_time"][11:16] for b in bookings if not b.get("deleted_at")}

        slots = []
        for hour in range(settings.START_HOUR, settings.END_HOUR + 1):
            time_str = f"{hour:02d}:00"
            if time_str not in busy:
                slots.append(time_str)

        if not slots:
            await callback.message.edit_text(
                f"На {_format_date_human(date_str)} нет свободных слотов.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text="⬅️ Назад к дате", callback_data="sched_back_to_date")
                ]]),
            )
            return

        rows, row = [], []
        for i, t in enumerate(slots):
            row.append(InlineKeyboardButton(text=t, callback_data=f"sched_create_time_{t}"))
            if len(row) == 4 or i == len(slots) - 1:
                rows.append(row)
                row = []
        rows.append([InlineKeyboardButton(text="⬅️ Назад к дате", callback_data="sched_back_to_date")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=rows)

        await callback.message.edit_text(
            f"Выберите время на {_format_date_human(date_str)}:",
            reply_markup=keyboard,
        )
        await state.set_state(ScheduleState.create_select_time)
    except Exception as e:
        logger.exception("time slots error")
        await callback.message.edit_text(f"Ошибка загрузки слотов: {e}")


@router.callback_query(F.data == "sched_back_to_date", ScheduleState.create_select_time)
async def sched_back_to_date(callback: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    year = user_data.get("calendar_year", datetime.now().year)
    month = user_data.get("calendar_month", datetime.now().month)
    await _show_calendar(callback, state, "Выберите дату:", year, month)
    await state.set_state(ScheduleState.create_select_date)
    await callback.answer()


@router.callback_query(F.data.startswith("sched_create_time_"), ScheduleState.create_select_time)
async def schedule_create_time_picked(callback: CallbackQuery, state: FSMContext):
    time_str = callback.data.rsplit("_", 1)[-1]
    user_data = await state.get_data()
    date_str = user_data["create_date"]
    sub_id = user_data["create_subscription_id"]
    client_name = user_data.get("create_client_name", "")

    start_time = f"{date_str}T{time_str}:00"
    end_dt = datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%S") + timedelta(hours=1)
    end_time = end_dt.strftime("%Y-%m-%dT%H:%M:%S")

    try:
        api = BackendAPIClient()
        await api.booking_create(
            subscription_id=sub_id,
            start_time=start_time,
            end_time=end_time,
        )
    except httpx.HTTPStatusError as e:
        detail = ""
        try:
            detail = e.response.json().get("detail", "")
        except Exception:
            pass
        text = f"Не удалось создать запись:\n{detail or e}"
        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔁 Выбрать другое время", callback_data="sched_back_to_date")],
                [InlineKeyboardButton(text="⬅️ В меню расписания", callback_data="sched_back_to_main")],
            ]),
        )
        await callback.answer()
        return
    except Exception as e:
        logger.exception("booking_create error")
        await callback.message.edit_text(f"Ошибка: {e}")
        await callback.answer()
        return

    text = (
        f"✅ Запись создана:\n\n"
        f"Клиент: {client_name}\n"
        f"Когда: {_format_date_human(date_str)} в {time_str}"
    )
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="⬅️ В меню расписания", callback_data="sched_back_to_main")
        ]]),
    )
    await state.set_state(ScheduleState.main)
    await callback.answer("Готово")


# =====================================================================
# УДАЛЕНИЕ ЗАПИСИ
# =====================================================================

@router.callback_query(F.data == "schedule_delete")
async def schedule_delete_start(callback: CallbackQuery, state: FSMContext):
    today = datetime.now()
    await state.update_data(calendar_year=today.year, calendar_month=today.month)
    await _show_calendar(callback, state, "Выберите дату записи для удаления:", today.year, today.month)
    await state.set_state(ScheduleState.delete_select_date)
    await callback.answer()


async def schedule_delete_select_booking(callback: CallbackQuery, state: FSMContext, date_str: str):
    user_data = await state.get_data()
    specialist_id = user_data.get("global_user_id")
    role = user_data.get("role", "specialist")

    try:
        api = BackendAPIClient()
        bookings = await api.bookings_for_date(
            date=date_str,
            specialist_id=specialist_id if role == "specialist" else None,
        )
        bookings = [b for b in bookings if not b.get("deleted_at")]
        bookings.sort(key=lambda b: b["start_time"])
    except Exception as e:
        logger.exception("delete list error")
        await callback.message.edit_text(f"Ошибка: {e}")
        return

    if not bookings:
        await callback.message.edit_text(
            f"На {_format_date_human(date_str)} нет записей.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="⬅️ Назад", callback_data="schedule_delete")
            ]]),
        )
        return

    await state.update_data(delete_date=date_str)

    buttons = []
    for b in bookings:
        time_str = b["start_time"][11:16]
        if b.get("booking_type") == "group" and b.get("group_name"):
            label = f"{time_str} — 👥 {b['group_name']} · {b.get('client_name', '?')}"
        else:
            label = f"{time_str} — {b.get('client_name', '—')}"
        if len(label) > 60:
            label = label[:57] + "…"
        buttons.append([InlineKeyboardButton(
            text=label,
            callback_data=f"sched_del_pick_{b['id']}",
        )])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="schedule_delete")])

    await callback.message.edit_text(
        f"Записи на {_format_date_human(date_str)} — выберите для удаления:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await state.set_state(ScheduleState.delete_select_booking)


@router.callback_query(F.data.startswith("sched_del_pick_"), ScheduleState.delete_select_booking)
async def schedule_delete_pick(callback: CallbackQuery, state: FSMContext):
    booking_id = int(callback.data.rsplit("_", 1)[-1])
    await state.update_data(delete_booking_id=booking_id)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑️ Да, удалить", callback_data="sched_del_confirm")],
        [InlineKeyboardButton(text="⬅️ Отмена", callback_data="schedule_delete")],
    ])
    await callback.message.edit_text(
        "Удалить запись?\n\n"
        "Сессия абонемента вернётся обратно (если бронь была активна).",
        reply_markup=keyboard,
    )
    await state.set_state(ScheduleState.delete_confirm)
    await callback.answer()


@router.callback_query(F.data == "sched_del_confirm", ScheduleState.delete_confirm)
async def schedule_delete_confirm(callback: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    booking_id = user_data.get("delete_booking_id")
    actor_id = user_data.get("global_user_id")
    try:
        api = BackendAPIClient()
        ok = await api.booking_delete(booking_id=booking_id, actor_id=actor_id)
    except Exception as e:
        logger.exception("booking_delete error")
        await callback.message.edit_text(f"Ошибка: {e}")
        await callback.answer()
        return

    text = "✅ Запись удалена." if ok else "Не удалось удалить запись."
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="⬅️ В меню расписания", callback_data="sched_back_to_main")
        ]]),
    )
    await state.set_state(ScheduleState.main)
    await callback.answer()


# =====================================================================
# Календарь — общий обработчик calendar_*
#
# Расширен для поддержки потока group_session: если активный state —
# GroupSessionState.select_date, обрабатываем как выбор даты для группового
# занятия.
# =====================================================================

@router.callback_query(F.data.startswith("calendar_"))
async def calendar_callback(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    action = parts[1]
    current_state = await state.get_state()

    if action == "day":
        date_str = f"{parts[2]}-{parts[3]}-{parts[4]}"

        # Расписание (свои состояния)
        if current_state == ScheduleState.view_select_date.state:
            await schedule_view_date(callback, state, date_str)
            await callback.answer()
            return
        if current_state == ScheduleState.create_select_date.state:
            await state.update_data(create_date=date_str)
            await _show_time_slots(callback, state)
            await callback.answer()
            return
        if current_state == ScheduleState.delete_select_date.state:
            await schedule_delete_select_booking(callback, state, date_str)
            await callback.answer()
            return

        # Group-session flow: проверяем по строковому имени состояния, чтобы
        # не тащить кросс-импорт
        if current_state and "GroupSessionState" in current_state and "select_date" in current_state:
            await state.update_data(gs_date=date_str)
            from handlers.group_session import gs_show_time_slots
            await gs_show_time_slots(callback, state)
            await callback.answer()
            return

        await callback.answer()
        return

    if action in ("prev", "next") and len(parts) > 2 and parts[2] == "month":
        user_data = await state.get_data()
        year = user_data.get("calendar_year", datetime.now().year)
        month = user_data.get("calendar_month", datetime.now().month)
        if action == "prev":
            year, month = (year - 1, 12) if month == 1 else (year, month - 1)
        else:
            year, month = (year + 1, 1) if month == 12 else (year, month + 1)
        await state.update_data(calendar_year=year, calendar_month=month)

        specialist_id = user_data.get("global_user_id")
        role = user_data.get("role", "specialist")
        busy = await _busy_dates_for_month(
            year, month, specialist_id if role == "specialist" else None
        )
        kb = get_calendar_keyboard(year, month, busy)
        await callback.message.edit_reply_markup(reply_markup=kb)
        await callback.answer()
        return

    if action == "cancel":
        await callback.message.delete()
        await cmd_schedule(callback.message, state)
        await callback.answer()
        return

    await callback.answer()
