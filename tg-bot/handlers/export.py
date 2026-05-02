from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from services.api_client import BackendAPIClient
from datetime import datetime, timedelta
from utils.dt import now as dt_now
import logging
from utils.errors import friendly_error
import io
import os

MONTH_NAMES = {
    1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель",
    5: "Май", 6: "Июнь", 7: "Июль", 8: "Август",
    9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь"
}

router = Router()
logger = logging.getLogger(__name__)

class ExportState(StatesGroup):
    main = State()
    select_period = State()
    select_month = State()

@router.message(F.text == "📊 Экспорт Excel")
async def cmd_export_excel(message: Message, state: FSMContext):
    data = await state.get_data()
    role = data.get("role", "specialist")

    if role not in ["admin", "methodist", "specialist"]:
        await message.answer("У вас нет прав для экспорта")
        from handlers.menu import show_main_menu
        await show_main_menu(message, state)
        return

    buttons = [
        [InlineKeyboardButton(text="📅 Текущий месяц", callback_data="export_current_month")],
        [InlineKeyboardButton(text="📆 Выбрать месяц", callback_data="export_select_month")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="export_back")]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await message.answer("📊 Выберите период для экспорта в Excel:", reply_markup=keyboard)
    await state.set_state(ExportState.select_period)

@router.callback_query(F.data == "export_back")
async def export_back(callback: CallbackQuery, state: FSMContext):
    from handlers.menu import show_main_menu
    await callback.message.delete()
    await show_main_menu(callback.message, state)
    await callback.answer()

@router.callback_query(F.data == "export_current_month")
async def export_current_month(callback: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    current_user_id = user_data.get("global_user_id")
    current_user_role = user_data.get("role", "specialist")

    today = dt_now()
    first_day = today.replace(day=1)
    last_day = (first_day + timedelta(days=32)).replace(day=1) - timedelta(days=1)

    start_date = first_day.strftime("%Y-%m-%d")
    end_date = last_day.strftime("%Y-%m-%d")
    month_year = first_day.strftime("%Y_%m")

    try:
        api_client = BackendAPIClient()

        if current_user_role == "specialist":
            excel_data = await api_client.export_excel(start_date, end_date, current_user_id, current_user_id, current_user_role)
        else:
            excel_data = await api_client.export_excel(start_date, end_date, None, current_user_id, current_user_role)

        if not excel_data:
            await callback.message.edit_text("Нет данных для экспорта")
            await callback.answer()
            return

        base_name = "Расписание.xlsx"
        name, ext = os.path.splitext(base_name)
        file = BufferedInputFile(
            file=excel_data,
            filename=f"{name}_{month_year}{ext}"
        )

        await callback.message.answer_document(
            document=file,
            caption=f"📊 Расписание за {MONTH_NAMES[first_day.month]} {first_day.year}"
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Error exporting Excel: {e}")
        await callback.message.edit_text(friendly_error(e, "export"))
        await callback.answer()

@router.callback_query(F.data == "export_select_month")
async def export_select_month(callback: CallbackQuery, state: FSMContext):
    current_year = dt_now().year
    months = []

    for month in range(1, 13):
        month_str = f"{current_year}_{month:02d}"
        month_name = f"{MONTH_NAMES[month]} {current_year}"
        months.append((month_str, month_name))

    buttons = []
    row = []
    for i, (month_str, month_name) in enumerate(months):
        row.append(InlineKeyboardButton(
            text=month_name,
            callback_data=f"export_month_{month_str}"
        ))
        if (i + 1) % 3 == 0 or i == len(months) - 1:
            buttons.append(row)
            row = []

    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="export_back")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_text("Выберите месяц:", reply_markup=keyboard)
    await state.set_state(ExportState.select_month)
    await callback.answer()

@router.callback_query(F.data.startswith("export_month_"))
async def export_month_selected(callback: CallbackQuery, state: FSMContext):
    month_str = callback.data.replace("export_month_", "")
    year, month = map(int, month_str.split("_"))

    first_day = datetime(year, month, 1)
    if month == 12:
        last_day = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = datetime(year, month + 1, 1) - timedelta(days=1)

    start_date = first_day.strftime("%Y-%m-%d")
    end_date = last_day.strftime("%Y-%m-%d")

    user_data = await state.get_data()
    current_user_id = user_data.get("global_user_id")
    current_user_role = user_data.get("role", "specialist")

    try:
        api_client = BackendAPIClient()

        if current_user_role == "specialist":
            excel_data = await api_client.export_excel(start_date, end_date, current_user_id, current_user_id, current_user_role)
        else:
            excel_data = await api_client.export_excel(start_date, end_date, None, current_user_id, current_user_role)

        if not excel_data:
            await callback.message.edit_text(f"Нет данных для экспорта за {MONTH_NAMES[month]} {year}")
            await callback.answer()
            return

        base_name = "Расписание.xlsx"
        name, ext = os.path.splitext(base_name)
        file = BufferedInputFile(
            file=excel_data,
            filename=f"{name}_{month_str}{ext}"
        )

        await callback.message.answer_document(
            document=file,
            caption=f"📊 Расписание за {MONTH_NAMES[month]} {year}"
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Error exporting Excel: {e}")
        await callback.message.edit_text(friendly_error(e, "export"))
        await callback.answer()