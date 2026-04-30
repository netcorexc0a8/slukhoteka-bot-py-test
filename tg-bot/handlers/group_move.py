"""
Перенос группового занятия (всех его броней разом) на новое время.

Поток:
  «📅 Расписание» → «🔁 Перенести групповое занятие»
    → выбор группы
    → дата старого занятия
    → выбор занятия из найденных (если несколько)
    → новая дата
    → новое время
    → POST /bookings/group/move → отчёт

Reuse: общий calendar_callback в schedule.py перенаправляет нажатия на дату
в этот хендлер по строковому имени состояния.
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
)

from config import settings
from keyboards.calendar import get_calendar_keyboard
from services.api_client import BackendAPIClient

router = Router()
logger = logging.getLogger(__name__)

DAY_NAMES = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]


def _fmt_date(s: str) -> str:
    d = datetime.strptime(s, "%Y-%m-%d")
    return f"{d.strftime('%d.%m.%Y')} ({DAY_NAMES[d.weekday()]})"


class GroupMoveState(StatesGroup):
    select_group = State()
    select_old_date = State()
    select_session = State()  # если в дне несколько занятий этой группы
    select_new_date = State()
    select_new_time = State()


# ---------------------------------------------------------------------
# Шаг 1: группа
# ---------------------------------------------------------------------

@router.callback_query(F.data == "schedule_move_group")
async def gm_start(callback: CallbackQuery, state: FSMContext):
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
            "Нет активных групп.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="⬅️ Назад", callback_data="sched_back_to_main")
            ]]),
        )
        await callback.answer()
        return

    await state.update_data(gm_groups_cache=groups)

    buttons = []
    for i, g in enumerate(groups):
        label = g.get("name", "?")
        if len(label) > 50:
            label = label[:47] + "…"
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"gm_pick_grp_{i}")])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="sched_back_to_main")])

    await callback.message.edit_text(
        "🔁 Перенос группового занятия\n\nВыберите группу:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await state.set_state(GroupMoveState.select_group)
    await callback.answer()


@router.callback_query(F.data.startswith("gm_pick_grp_"), GroupMoveState.select_group)
async def gm_group_picked(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.rsplit("_", 1)[-1])
    user_data = await state.get_data()
    groups = user_data.get("gm_groups_cache") or []
    if idx >= len(groups):
        await callback.answer("Группа не найдена.", show_alert=True)
        return
    g = groups[idx]
    await state.update_data(gm_group_id=g["id"], gm_group_name=g["name"])

    today = datetime.now()
    await state.update_data(calendar_year=today.year, calendar_month=today.month)
    await callback.message.edit_text(
        f"Группа: «{g['name']}»\nВыберите дату занятия, которое переносим:",
        reply_markup=get_calendar_keyboard(today.year, today.month, []),
    )
    await state.set_state(GroupMoveState.select_old_date)
    await callback.answer()


# ---------------------------------------------------------------------
# Шаг 2: старая дата (через calendar_callback в schedule.py)
# Шаг 3: выбор конкретного занятия в этот день (если их несколько)
# ---------------------------------------------------------------------

async def gm_after_old_date(callback: CallbackQuery, state: FSMContext, date_str: str):
    user_data = await state.get_data()
    group_id = user_data["gm_group_id"]
    api = BackendAPIClient()
    try:
        bookings = await api.bookings_for_date(date=date_str)
    except Exception as e:
        logger.exception("bookings_for_date error")
        await callback.message.edit_text(f"Ошибка: {e}")
        return

    # Только групповые брони этой группы
    related = [
        b for b in bookings
        if not b.get("deleted_at")
        and b.get("group_id") == group_id
        and b.get("booking_type") == "group"
        and b.get("status") not in ("cancelled", "specialist_cancelled")
    ]

    # Группируем по start_time (одно занятие = много броней)
    by_start: dict[str, list] = {}
    for b in related:
        by_start.setdefault(b["start_time"], []).append(b)

    if not by_start:
        await callback.message.edit_text(
            f"В этот день у группы «{user_data['gm_group_name']}» нет занятий.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="⬅️ Назад", callback_data="schedule_move_group")
            ]]),
        )
        return

    if len(by_start) == 1:
        only_start = next(iter(by_start.keys()))
        await _go_to_new_date(callback, state, only_start, by_start[only_start])
        return

    # Несколько занятий в день — даём выбрать
    starts = sorted(by_start.keys())
    await state.update_data(gm_old_date=date_str)
    buttons = []
    for st in starts:
        time_label = st[11:16]
        count = len(by_start[st])
        buttons.append([InlineKeyboardButton(
            text=f"{time_label} ({count} чел.)",
            callback_data=f"gm_pick_session_{time_label}",
        )])
    # Кэшируем by_start для второго шага
    await state.update_data(gm_sessions_cache={k: [b["id"] for b in v] for k, v in by_start.items()})
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="schedule_move_group")])
    await callback.message.edit_text(
        f"В этот день несколько занятий группы «{user_data['gm_group_name']}». Выберите:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await state.set_state(GroupMoveState.select_session)


@router.callback_query(F.data.startswith("gm_pick_session_"), GroupMoveState.select_session)
async def gm_session_picked(callback: CallbackQuery, state: FSMContext):
    time_label = callback.data.rsplit("_", 1)[-1]
    user_data = await state.get_data()
    date_str = user_data["gm_old_date"]
    cache = user_data.get("gm_sessions_cache") or {}
    # Найти полный start_time по time_label
    full_start = next((k for k in cache if k[11:16] == time_label), None)
    if not full_start:
        await callback.answer("Занятие не найдено.", show_alert=True)
        return
    # client_count для отчёта
    booking_ids = cache[full_start]
    await _go_to_new_date(callback, state, full_start, [{"id": bid} for bid in booking_ids])


async def _go_to_new_date(
    callback: CallbackQuery, state: FSMContext, old_start_iso: str, sample_bookings: list,
):
    """Сохраняем старое start_time, спрашиваем новую дату."""
    await state.update_data(
        gm_old_start=old_start_iso,
        gm_session_count=len(sample_bookings),
    )
    today = datetime.now()
    await state.update_data(calendar_year=today.year, calendar_month=today.month)
    user_data = await state.get_data()
    await callback.message.edit_text(
        f"Группа: «{user_data['gm_group_name']}»\n"
        f"Старое время: {old_start_iso[:10]} {old_start_iso[11:16]}\n"
        f"Участников: {user_data['gm_session_count']}\n\n"
        f"Выберите новую дату:",
        reply_markup=get_calendar_keyboard(today.year, today.month, []),
    )
    await state.set_state(GroupMoveState.select_new_date)
    await callback.answer()


# ---------------------------------------------------------------------
# Шаг 4: новая дата (через calendar_callback в schedule.py)
# ---------------------------------------------------------------------

async def gm_after_new_date(callback: CallbackQuery, state: FSMContext, date_str: str):
    await state.update_data(gm_new_date=date_str)
    user_data = await state.get_data()

    # Слоты — без учёта занятости (как и в gs_show_time_slots), потому что
    # на новое время backend всё равно проверит конфликт ведущего и weekly limit.
    slots = [f"{h:02d}:00" for h in range(settings.START_HOUR, settings.END_HOUR + 1)]
    rows, row = [], []
    for i, t in enumerate(slots):
        row.append(InlineKeyboardButton(text=t, callback_data=f"gm_pick_time_{t}"))
        if len(row) == 4 or i == len(slots) - 1:
            rows.append(row)
            row = []
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="schedule_move_group")])

    await callback.message.edit_text(
        f"Группа: «{user_data['gm_group_name']}»\n"
        f"Новая дата: {_fmt_date(date_str)}\n\n"
        f"Выберите время:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )
    await state.set_state(GroupMoveState.select_new_time)


# ---------------------------------------------------------------------
# Шаг 5: новое время → запрос на бэкенд
# ---------------------------------------------------------------------

@router.callback_query(F.data.startswith("gm_pick_time_"), GroupMoveState.select_new_time)
async def gm_time_picked(callback: CallbackQuery, state: FSMContext):
    time_str = callback.data.rsplit("_", 1)[-1]
    user_data = await state.get_data()

    new_start = f"{user_data['gm_new_date']}T{time_str}:00"
    api = BackendAPIClient()

    try:
        result = await api.booking_group_move(
            group_id=user_data["gm_group_id"],
            old_start=user_data["gm_old_start"],
            new_start=new_start,
        )
    except httpx.HTTPStatusError as e:
        detail = ""
        try:
            detail = e.response.json().get("detail", "")
        except Exception:
            pass
        await callback.message.edit_text(
            f"Не удалось перенести занятие:\n{detail or e}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔁 Другое время", callback_data="gm_back_to_new_date")],
                [InlineKeyboardButton(text="⬅️ В меню", callback_data="sched_back_to_main")],
            ]),
        )
        await callback.answer()
        return
    except Exception as e:
        logger.exception("booking_group_move error")
        await callback.message.edit_text(f"Ошибка: {e}")
        await callback.answer()
        return

    moved = result.get("moved", [])
    failed = result.get("failed", [])

    lines = [
        f"✅ Занятие перенесено." if moved else "⚠️ Ничего не перенесено.",
        f"Группа: «{user_data['gm_group_name']}»",
        f"Старое: {user_data['gm_old_start'][:10]} {user_data['gm_old_start'][11:16]}",
        f"Новое: {_fmt_date(user_data['gm_new_date'])} в {time_str}",
        "",
    ]
    if moved:
        lines.append(f"Перенесено броней: {len(moved)}")
    if failed:
        lines.append("")
        lines.append(f"Не удалось ({len(failed)}):")
        for item in failed:
            err = (item.get("reason") or "").replace("\n", " ")
            if len(err) > 80:
                err = err[:77] + "…"
            lines.append(f"  • {item.get('client', '?')}: {err}")

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="⬅️ В меню расписания", callback_data="sched_back_to_main")
        ]]),
    )
    await state.set_state(None)
    await callback.answer("Готово")


@router.callback_query(F.data == "gm_back_to_new_date")
async def gm_back_to_new_date(callback: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    year = user_data.get("calendar_year", datetime.now().year)
    month = user_data.get("calendar_month", datetime.now().month)
    await callback.message.edit_text(
        f"Группа: «{user_data['gm_group_name']}»\nВыберите новую дату:",
        reply_markup=get_calendar_keyboard(year, month, []),
    )
    await state.set_state(GroupMoveState.select_new_date)
    await callback.answer()
