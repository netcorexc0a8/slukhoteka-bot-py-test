from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from services.api_client import BackendAPIClient
from datetime import datetime, timedelta
from utils.dt import now as dt_now
from utils.errors import friendly_error
from utils.guards import require_role
import logging

router = Router()
logger = logging.getLogger(__name__)

MONTH_NAMES = {
    1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель",
    5: "Май", 6: "Июнь", 7: "Июль", 8: "Август",
    9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь"
}


class ICSState(StatesGroup):
    select_period = State()
    select_month = State()


@router.message(F.text == "📆 Экспорт ICS")
@require_role("admin")
async def cmd_export_ics(message: Message, state: FSMContext):
    buttons = [
        [InlineKeyboardButton(text="📅 Текущий месяц", callback_data="ics_current_month")],
        [InlineKeyboardButton(text="📆 Выбрать месяц", callback_data="ics_select_month")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="ics_back")],
    ]
    await message.answer(
        "📆 Выберите период для экспорта ICS:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await state.set_state(ICSState.select_period)


@router.callback_query(F.data == "ics_back")
async def ics_back(callback: CallbackQuery, state: FSMContext):
    from handlers.menu import show_main_menu
    await callback.message.delete()
    await show_main_menu(callback.message, state)
    await callback.answer()


@router.callback_query(F.data == "ics_current_month")
async def ics_current_month(callback: CallbackQuery, state: FSMContext):
    today = dt_now()
    first_day = today.replace(day=1)
    await _do_export_ics(callback, first_day.year, first_day.month)


@router.callback_query(F.data == "ics_select_month")
async def ics_select_month(callback: CallbackQuery, state: FSMContext):
    current_year = dt_now().year
    buttons = []
    row = []
    for i, month in enumerate(range(1, 13)):
        month_str = f"{current_year}_{month:02d}"
        row.append(InlineKeyboardButton(
            text=f"{MONTH_NAMES[month]} {current_year}",
            callback_data=f"ics_month_{month_str}",
        ))
        if len(row) == 3 or i == 11:
            buttons.append(row)
            row = []
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="ics_back")])

    await callback.message.edit_text(
        "Выберите месяц:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await state.set_state(ICSState.select_month)
    await callback.answer()


@router.callback_query(F.data.startswith("ics_month_"))
async def ics_month_selected(callback: CallbackQuery, state: FSMContext):
    month_str = callback.data.replace("ics_month_", "")
    year, month = map(int, month_str.split("_"))
    await _do_export_ics(callback, year, month)


async def _do_export_ics(callback: CallbackQuery, year: int, month: int):
    """Генерирует и отправляет ICS файл за указанный месяц."""
    first_day = datetime(year, month, 1)
    if month == 12:
        last_day = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = datetime(year, month + 1, 1) - timedelta(days=1)

    start_date = first_day.strftime("%Y-%m-%d")
    end_date = last_day.strftime("%Y-%m-%d")

    await callback.message.edit_text("⏳ Формирую ICS файл...")

    try:
        api_client = BackendAPIClient()
        bookings = await api_client.bookings_for_range(start_date, end_date)
        bookings = [
            b for b in bookings
            if not b.get("deleted_at")
            and b.get("status") not in ("cancelled", "specialist_cancelled")
        ]

        if not bookings:
            await callback.message.edit_text(
                f"Нет данных для экспорта за {MONTH_NAMES[month]} {year}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text="⬅️ Назад", callback_data="ics_select_month")
                ]]),
            )
            await callback.answer()
            return

        ics_content = generate_ics(bookings)
        file = BufferedInputFile(
            file=ics_content.encode("utf-8"),
            filename=f"schedule_{start_date}_{end_date}.ics",
        )

        await callback.message.answer_document(
            document=file,
            caption=f"📆 ICS файл за {MONTH_NAMES[month]} {year} ({len(bookings)} записей)",
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Error exporting ICS: {e}")
        await callback.message.edit_text(friendly_error(e, "export_ics"))
        await callback.answer()


def _ics_escape(s: str) -> str:
    """Базовый escape для ICS-полей."""
    if s is None:
        return ""
    return s.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;").replace("\n", "\\n")


def generate_ics(bookings):
    from config import settings as _s
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Slukhoteka//Schedule//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Слухотека",
        f"X-WR-TIMEZONE:{_s.TIMEZONE}",
        "X-WR-CALDESC:Расписание записи клиентов",
    ]

    for b in bookings:
        start_time = b["start_time"].replace("-", "").replace(":", "").replace("T", "")
        end_time = b["end_time"].replace("-", "").replace(":", "").replace("T", "")
        if "+" in start_time:
            start_time = start_time.split("+")[0]
        if "+" in end_time:
            end_time = end_time.split("+")[0]
        start_time = start_time.rstrip("Z")[:15]
        end_time = end_time.rstrip("Z")[:15]

        client_name = b.get("client_name") or "Запись"
        specialist = b.get("specialist_name") or ""
        service = b.get("service_name") or ""

        description_parts = []
        if specialist:
            description_parts.append(f"Специалист: {specialist}")
        if service:
            description_parts.append(f"Услуга: {service}")
        if b.get("subscription_total"):
            description_parts.append(
                f"Сессия {b.get('subscription_used') or 0}/{b['subscription_total']}"
            )
        description = " | ".join(description_parts) or "Запись клиента"

        lines.extend([
            "BEGIN:VEVENT",
            f"UID:booking-{b['id']}@slukhoteka",
            f"DTSTART:{start_time}",
            f"DTEND:{end_time}",
            f"SUMMARY:{_ics_escape(client_name)}",
            f"DESCRIPTION:{_ics_escape(description)}",
            "END:VEVENT",
        ])

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)