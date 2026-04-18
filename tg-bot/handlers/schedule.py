from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
from services.api_client import BackendAPIClient
from keyboards.calendar import get_calendar_keyboard
from config import settings
import logging

router = Router()
logger = logging.getLogger(__name__)

async def get_busy_dates_for_month(year: int, month: int, user_id=None) -> list:
    try:
        api_client = BackendAPIClient()
        first_day = datetime(year, month, 1)
        if month == 12:
            last_day = datetime(year + 1, 1, 1)
        else:
            last_day = datetime(year, month + 1, 1)
        
        schedules = await api_client.schedule_get_all(
            start_date=first_day.strftime("%Y-%m-%d"),
            end_date=last_day.strftime("%Y-%m-%d"),
            user_id=user_id
        )
        
        busy_dates = []
        for sched in schedules:
            date_str = sched["start_time"][:10]
            if date_str not in busy_dates:
                busy_dates.append(date_str)
        
        return busy_dates
    except Exception as e:
        logger.error(f"Error getting busy dates: {e}")
        return []

class ScheduleState(StatesGroup):
    main = State()
    selecting_date = State()
    viewing = State()
    create_select_date = State()
    create_select_time = State()
    create_select_client = State()
    create_select_recurrence = State()
    create_enter_name = State()
    edit_select_date = State()
    edit_select_schedule = State()
    edit_select_scope = State()
    edit_enter_name = State()
    move_select_date = State()
    move_select_schedule = State()
    move_select_new_date = State()
    move_select_time = State()
    move_select_scope = State()
    delete_select_date = State()
    delete_select_schedule = State()
    delete_select_scope = State()
    delete_confirm = State()

@router.message(F.text == "📅 Расписание")
async def cmd_schedule(message: Message, state: FSMContext):
    buttons = [
        [InlineKeyboardButton(text="📋 Посмотреть расписание", callback_data="schedule_view")],
        [InlineKeyboardButton(text="➕ Создать запись", callback_data="schedule_create")],
        [InlineKeyboardButton(text="✏️ Изменить запись", callback_data="schedule_edit")],
        [InlineKeyboardButton(text="🔄 Перенести запись", callback_data="schedule_move")],
        [InlineKeyboardButton(text="🗑️ Удалить запись", callback_data="schedule_delete")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="schedule_back")]
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

@router.callback_query(F.data == "schedule_view")
async def schedule_view_start(callback: CallbackQuery, state: FSMContext):
    today = datetime.now()
    await state.update_data(calendar_year=today.year, calendar_month=today.month)
    
    user_data = await state.get_data()
    user_id = user_data.get("global_user_id")
    role = user_data.get("role", "specialist")
    
    busy_dates = await get_busy_dates_for_month(today.year, today.month, user_id if role == "specialist" else None)
    calendar_kb = get_calendar_keyboard(today.year, today.month, busy_dates)
    await callback.message.edit_text("Выберите дату для просмотра:", reply_markup=calendar_kb)
    await state.set_state(ScheduleState.selecting_date)
    await callback.answer()

@router.callback_query(F.data == "schedule_create")
async def schedule_create_start(callback: CallbackQuery, state: FSMContext):
    await schedule_create_select_date(callback, state)

async def schedule_create_select_date(callback: CallbackQuery, state: FSMContext):
    today = datetime.now()
    await state.update_data(calendar_year=today.year, calendar_month=today.month)
    
    user_data = await state.get_data()
    user_id = user_data.get("global_user_id")
    role = user_data.get("role", "specialist")
    
    busy_dates = await get_busy_dates_for_month(today.year, today.month, user_id if role == "specialist" else None)
    calendar_kb = get_calendar_keyboard(today.year, today.month, busy_dates)
    await callback.message.edit_text("Выберите дату:", reply_markup=calendar_kb)
    await state.set_state(ScheduleState.create_select_date)
    await callback.answer()

@router.callback_query(F.data == "schedule_edit")
async def schedule_edit_start(callback: CallbackQuery, state: FSMContext):
    today = datetime.now()
    await state.update_data(calendar_year=today.year, calendar_month=today.month)
    
    user_data = await state.get_data()
    user_id = user_data.get("global_user_id")
    role = user_data.get("role", "specialist")
    
    busy_dates = await get_busy_dates_for_month(today.year, today.month, user_id if role == "specialist" else None)
    calendar_kb = get_calendar_keyboard(today.year, today.month, busy_dates)
    await callback.message.edit_text("Выберите дату:", reply_markup=calendar_kb)
    await state.set_state(ScheduleState.edit_select_date)
    await callback.answer()

@router.callback_query(F.data == "schedule_move")
async def schedule_move_start(callback: CallbackQuery, state: FSMContext):
    today = datetime.now()
    await state.update_data(calendar_year=today.year, calendar_month=today.month)
    
    user_data = await state.get_data()
    user_id = user_data.get("global_user_id")
    role = user_data.get("role", "specialist")
    
    busy_dates = await get_busy_dates_for_month(today.year, today.month, user_id if role == "specialist" else None)
    calendar_kb = get_calendar_keyboard(today.year, today.month, busy_dates)
    await callback.message.edit_text("Выберите дату:", reply_markup=calendar_kb)
    await state.set_state(ScheduleState.move_select_date)
    await callback.answer()

@router.callback_query(F.data == "schedule_delete")
async def schedule_delete_start(callback: CallbackQuery, state: FSMContext):
    today = datetime.now()
    await state.update_data(calendar_year=today.year, calendar_month=today.month)
    
    user_data = await state.get_data()
    user_id = user_data.get("global_user_id")
    role = user_data.get("role", "specialist")
    
    busy_dates = await get_busy_dates_for_month(today.year, today.month, user_id if role == "specialist" else None)
    calendar_kb = get_calendar_keyboard(today.year, today.month, busy_dates)
    await callback.message.edit_text("Выберите дату:", reply_markup=calendar_kb)
    await state.set_state(ScheduleState.delete_select_date)
    await callback.answer()

@router.callback_query(F.data.startswith("calendar_"))
async def calendar_callback(callback: CallbackQuery, state: FSMContext):
    data_parts = callback.data.split("_")
    action = data_parts[1]

    if action == "day":
        date_str = f"{data_parts[2]}-{data_parts[3]}-{data_parts[4]}"
        current_state = await state.get_state()

        if current_state == ScheduleState.selecting_date:
            await schedule_view_date(callback, state, date_str)
        elif current_state == ScheduleState.create_select_date:
            await state.update_data(create_date=date_str)
            await schedule_create_select_time(callback, state)
        elif current_state == ScheduleState.edit_select_date:
            await schedule_edit_select_schedule(callback, state, date_str)
        elif current_state == ScheduleState.move_select_date:
            await schedule_move_select_schedule(callback, state, date_str)
        elif current_state == ScheduleState.move_select_new_date:
            await state.update_data(move_new_date=date_str)
            await schedule_move_select_time(callback, state)
        elif current_state == ScheduleState.delete_select_date:
            await schedule_delete_select_schedule(callback, state, date_str)

    elif action == "prev" and len(data_parts) > 2 and data_parts[2] == "month":
        user_data = await state.get_data()
        calendar_year = user_data.get("calendar_year", datetime.now().year)
        calendar_month = user_data.get("calendar_month", datetime.now().month)
        user_id = user_data.get("global_user_id")
        role = user_data.get("role", "specialist")

        if calendar_month == 1:
            prev_year = calendar_year - 1
            prev_month = 12
        else:
            prev_year = calendar_year
            prev_month = calendar_month - 1

        await state.update_data(calendar_year=prev_year, calendar_month=prev_month)
        
        busy_dates = await get_busy_dates_for_month(prev_year, prev_month, user_id if role == "specialist" else None)
        calendar_kb = get_calendar_keyboard(prev_year, prev_month, busy_dates)
        await callback.message.edit_reply_markup(reply_markup=calendar_kb)
        await callback.answer()

    elif action == "next" and len(data_parts) > 2 and data_parts[2] == "month":
        user_data = await state.get_data()
        calendar_year = user_data.get("calendar_year", datetime.now().year)
        calendar_month = user_data.get("calendar_month", datetime.now().month)
        user_id = user_data.get("global_user_id")
        role = user_data.get("role", "specialist")

        if calendar_month == 12:
            next_year = calendar_year + 1
            next_month = 1
        else:
            next_year = calendar_year
            next_month = calendar_month + 1

        await state.update_data(calendar_year=next_year, calendar_month=next_month)
        
        busy_dates = await get_busy_dates_for_month(next_year, next_month, user_id if role == "specialist" else None)
        calendar_kb = get_calendar_keyboard(next_year, next_month, busy_dates)
        await callback.message.edit_reply_markup(reply_markup=calendar_kb)
        await callback.answer()

    elif action == "cancel":
        await callback.message.delete()
        await cmd_schedule(callback.message, state)
        await callback.answer()
    else:
        await callback.answer()

async def schedule_view_date(callback: CallbackQuery, state: FSMContext, date_str: str):
    user_data = await state.get_data()
    user_id = user_data.get("global_user_id")
    role = user_data.get("role", "specialist")

    try:
        api_client = BackendAPIClient()
        schedules = await api_client.schedule_get(date=date_str, user_id=user_id if role == "specialist" else None, include_deleted=True)

        active_schedules = [s for s in schedules if not s.get('deleted_at')]
        deleted_schedules = [s for s in schedules if s.get('deleted_at')]

        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        formatted_date = date_obj.strftime("%d.%m.%Y")

        day_names = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
        day_name = day_names[date_obj.weekday()]

        if not active_schedules:
            await callback.message.edit_text(f"На {formatted_date} ({day_name}) нет записей")
            await state.set_state(ScheduleState.viewing)
            return

        response_text = f"📅 Записи на {formatted_date} ({day_name}):\n\n"
        buttons = []
        for sched in active_schedules:
            time_str = sched["start_time"][11:16]
            user_name = sched.get("user_name", "")
            if user_name:
                response_text += f"• {time_str} - {sched['title']} ({user_name})\n"
            else:
                response_text += f"• {time_str} - {sched['title']}\n"

            if user_name:
                buttons.append([
                    InlineKeyboardButton(
                        text=f"{time_str} - {sched['title']} ({user_name})",
                        callback_data=f"schedule_delete_select_{sched['id']}"
                    )
                ])
            else:
                buttons.append([
                    InlineKeyboardButton(
                        text=f"{time_str} - {sched['title']}",
                        callback_data=f"schedule_delete_select_{sched['id']}"
                    )
                ])

        response_text = f"📅 Записи на {formatted_date} ({day_name}):\n\n"
        buttons = []
        for sched in schedules:
            time_str = sched["start_time"][11:16]
            user_name = sched.get("user_name", "")
            if user_name:
                response_text += f"• {time_str} - {sched['title']} ({user_name})\n"
            else:
                response_text += f"• {time_str} - {sched['title']}\n"

        buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="schedule_back")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await callback.message.edit_text(response_text, reply_markup=keyboard)
        await state.set_state(ScheduleState.viewing)

    except Exception as e:
        logger.error(f"Error loading schedule: {e}")
        await callback.message.edit_text(f"Ошибка загрузки расписания: {e}")
        await state.set_state(ScheduleState.viewing)

async def schedule_create_select_time(callback: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    date_str = user_data.get("create_date")
    user_id = user_data.get("global_user_id")

    try:
        api_client = BackendAPIClient()
        schedules = await api_client.schedule_get(date=date_str, user_id=user_id)

        busy_times = [s["start_time"][11:16] for s in schedules]
        available_times = []
        for hour in range(settings.START_HOUR, settings.END_HOUR + 1):
            for minute in range(0, 60, settings.TIME_SLOT_DURATION * 60):
                time_str = f"{hour:02d}:{minute:02d}"
                if time_str not in busy_times:
                    available_times.append(time_str)

        if not available_times:
            await callback.message.edit_text(f"На {date_str} нет доступных слотов")
            return

        buttons = []
        row = []
        for i, time_str in enumerate(available_times):
            row.append(InlineKeyboardButton(
                text=time_str,
                callback_data=f"schedule_create_time_{time_str}"
            ))
            if len(row) == 4 or i == len(available_times) - 1:
                buttons.append(row)
                row = []

        buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="schedule_create")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        day_names = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        day_name = day_names[date_obj.weekday()]
        formatted_date = date_obj.strftime("%d.%m.%Y")

        await callback.message.edit_text(f"Выберите время для записи на {formatted_date} ({day_name}):", reply_markup=keyboard)
        await state.set_state(ScheduleState.create_select_time)

    except Exception as e:
        logger.error(f"Error loading schedule: {e}")
        await callback.message.edit_text(f"Ошибка загрузки расписания: {e}")

async def schedule_move_select_time(callback: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    date_str = user_data.get("move_new_date")
    user_id = user_data.get("global_user_id")
    schedule_id = user_data.get("move_schedule_id")

    try:
        api_client = BackendAPIClient()
        schedules = await api_client.schedule_get(date=date_str, user_id=user_id)

        busy_times = [s["start_time"][11:16] for s in schedules]
        available_times = []
        for hour in range(settings.START_HOUR, settings.END_HOUR + 1):
            for minute in range(0, 60, settings.TIME_SLOT_DURATION * 60):
                time_str = f"{hour:02d}:{minute:02d}"
                if time_str not in busy_times:
                    available_times.append(time_str)

        if not available_times:
            await callback.message.edit_text(f"На {date_str} нет доступных слотов")
            return

        buttons = []
        row = []
        for i, time_str in enumerate(available_times):
            row.append(InlineKeyboardButton(
                text=time_str,
                callback_data=f"schedule_move_time_{time_str}"
            ))
            if len(row) == 4 or i == len(available_times) - 1:
                buttons.append(row)
                row = []

        buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="schedule_move")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        day_names = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        day_name = day_names[date_obj.weekday()]
        formatted_date = date_obj.strftime("%d.%m.%Y")

        await callback.message.edit_text(f"Выберите новое время для записи на {formatted_date} ({day_name}):", reply_markup=keyboard)
        await state.set_state(ScheduleState.move_select_time)

    except Exception as e:
        logger.error(f"Error loading schedule: {e}")
        await callback.message.edit_text(f"Ошибка загрузки расписания: {e}")

@router.callback_query(F.data.startswith("schedule_create_time_"))
async def schedule_create_time_selected(callback: CallbackQuery, state: FSMContext):
    time_str = callback.data.split("_")[-1]
    await state.update_data(create_time=time_str)

    user_data = await state.get_data()
    user_id = user_data.get("global_user_id")

    try:
        api_client = BackendAPIClient()
        schedules = await api_client.schedule_get_all(
            start_date="2020-01-01",
            end_date="2030-12-31",
            user_id=user_id
        )

        client_names = list(set(s['title'] for s in schedules if s['title']))

        await state.update_data(create_client_names=client_names)

        buttons = []
        for i, name in enumerate(client_names):
            buttons.append([InlineKeyboardButton(
                text=name,
                callback_data=f"schedule_create_client_idx_{i}"
            )])

        buttons.append([InlineKeyboardButton(text="➕ Новый клиент", callback_data="schedule_create_new_client")])
        buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="schedule_create")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await callback.message.edit_text("Выберите клиента:", reply_markup=keyboard)
        await state.set_state(ScheduleState.create_select_client)
        await callback.answer()

    except Exception as e:
        logger.error(f"Error loading schedules: {e}")
        await callback.message.edit_text("Введите имя клиента:")
        await state.set_state(ScheduleState.create_enter_name)
        await callback.answer()

@router.message(ScheduleState.create_enter_name)
async def schedule_create_name_input(message: Message, state: FSMContext):
    client_name = message.text.strip()

    if not client_name:
        await message.answer("Имя клиента не может быть пустым")
        return

    user_data = await state.get_data()
    user_id = user_data.get("global_user_id")

    if not user_id:
        await message.answer("Ошибка авторизации. Пожалуйста, авторизуйтесь заново.")
        logger.error(f"Missing global_user_id in state data: {user_data}")
        return

    user_id = int(user_id)
    date_str = user_data.get("create_date")
    time_str = user_data.get("create_time")

    try:
        api_client = BackendAPIClient()

        await state.update_data(create_client_name=client_name)

        buttons = [
            [InlineKeyboardButton(text="🔁 Повторять еженедельно", callback_data="schedule_create_recurrence_yes")],
            [InlineKeyboardButton(text="📅 Однократная запись", callback_data="schedule_create_recurrence_no")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="schedule_create")]
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await message.answer(f"Создать повторяющуюся еженедельно запись для {client_name}?", reply_markup=keyboard)
        await state.set_state(ScheduleState.create_select_recurrence)

    except Exception as e:
        logger.error(f"Error processing client name: {e}")
        await message.answer(f"Ошибка обработки имени клиента: {e}")

async def schedule_edit_select_schedule(callback: CallbackQuery, state: FSMContext, date_str: str):
    user_data = await state.get_data()
    current_user_id = user_data.get("global_user_id")
    role = user_data.get("role", "specialist")

    try:
        api_client = BackendAPIClient()
        schedules = await api_client.schedule_get(date=date_str, user_id=current_user_id if role == "specialist" else None)

        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        formatted_date = date_obj.strftime("%d.%m.%Y")

        if not schedules:
            await callback.message.edit_text(f"На {formatted_date} нет записей")
            return

        buttons = []
        for sched in schedules:
            time_str = sched["start_time"][11:16]
            user_name = sched.get("user_name", "")
            if user_name:
                buttons.append([InlineKeyboardButton(
                    text=f"{time_str} - {sched['title']} ({user_name})",
                    callback_data=f"schedule_edit_select_{sched['id']}"
                )])
            else:
                buttons.append([InlineKeyboardButton(
                    text=f"{time_str} - {sched['title']}",
                    callback_data=f"schedule_edit_select_{sched['id']}"
                )])

        buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="schedule_edit")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await callback.message.edit_text("Выберите запись для изменения:", reply_markup=keyboard)
        await state.set_state(ScheduleState.edit_select_schedule)
        await callback.answer()

    except Exception as e:
        logger.error(f"Error loading schedule: {e}")
        await callback.message.edit_text(f"Ошибка загрузки расписания: {e}")
        await callback.answer()

@router.callback_query(F.data.startswith("schedule_edit_select_"))
async def schedule_edit_select(callback: CallbackQuery, state: FSMContext):
    schedule_id = int(callback.data.split("_")[-1])

    try:
        api_client = BackendAPIClient()

        user_data = await state.get_data()
        current_user_id = user_data.get("global_user_id")

        schedules = await api_client.schedule_get_all(
            start_date=datetime.now().strftime("%Y-%m-%d"),
            end_date=(datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d"),
            user_id=current_user_id
        )

        schedule = next((s for s in schedules if s['id'] == schedule_id), None)

        if not schedule:
            await callback.message.edit_text("Запись не найдена")
            await callback.answer()
            return

        await state.update_data(edit_schedule_id=schedule_id)

        if schedule.get('is_recurring') and schedule.get('recurrence_group_id'):
            buttons = [
                [InlineKeyboardButton(text="📝 Только эту запись", callback_data="schedule_edit_scope_current")],
                [InlineKeyboardButton(text="📋 Всю серию", callback_data="schedule_edit_scope_series")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="schedule_edit")]
            ]
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

            await callback.message.edit_text("Изменить только эту запись или всю серию?", reply_markup=keyboard)
            await state.set_state(ScheduleState.edit_select_scope)
            await callback.answer()
        else:
            await callback.message.edit_text("Введите новое имя клиента:")
            await state.set_state(ScheduleState.edit_enter_name)
            await callback.answer()

    except Exception as e:
        logger.error(f"Error selecting schedule for edit: {e}")
        await callback.message.edit_text(f"Ошибка: {e}")
        await callback.answer()

@router.message(ScheduleState.edit_enter_name)
async def schedule_edit_name_input(message: Message, state: FSMContext):
    new_name = message.text.strip()

    if not new_name:
        await message.answer("Имя клиента не может быть пустым")
        return

    user_data = await state.get_data()
    schedule_id = user_data.get("edit_schedule_id")
    edit_scope = user_data.get("edit_scope", "current")

    try:
        api_client = BackendAPIClient()

        if edit_scope == "series":
            schedules = await api_client.schedule_get_all(
                start_date=datetime.now().strftime("%Y-%m-%d"),
                end_date=(datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
            )

            schedule = next((s for s in schedules if s['id'] == schedule_id), None)
            if schedule and schedule.get('recurrence_group_id'):
                await api_client.schedule_update_series(schedule['recurrence_group_id'], title=new_name)
                await message.answer(f"✅ Имя клиента успешно изменено на '{new_name}' для всей серии!")
            else:
                await message.answer("Ошибка: не удалось найти серию записей")
        else:
            await api_client.schedule_update(schedule_id, title=new_name)
            await message.answer(f"✅ Имя клиента успешно изменено на '{new_name}'")

        await state.clear()
        await cmd_schedule(message, state)

    except Exception as e:
        logger.error(f"Error updating schedule: {e}")
        await message.answer(f"Ошибка изменения записи: {e}")

async def schedule_move_select_schedule(callback: CallbackQuery, state: FSMContext, date_str: str):
    user_data = await state.get_data()
    current_user_id = user_data.get("global_user_id")
    role = user_data.get("role", "specialist")

    try:
        api_client = BackendAPIClient()
        schedules = await api_client.schedule_get(date=date_str, user_id=current_user_id if role == "specialist" else None)

        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        formatted_date = date_obj.strftime("%d.%m.%Y")

        if not schedules:
            await callback.message.edit_text(f"На {formatted_date} нет записей")
            return

        buttons = []
        for sched in schedules:
            time_str = sched["start_time"][11:16]
            user_name = sched.get("user_name", "")
            if user_name:
                buttons.append([InlineKeyboardButton(
                    text=f"{time_str} - {sched['title']} ({user_name})",
                    callback_data=f"schedule_move_select_{sched['id']}_{date_str}"
                )])
            else:
                buttons.append([InlineKeyboardButton(
                    text=f"{time_str} - {sched['title']}",
                    callback_data=f"schedule_move_select_{sched['id']}_{date_str}"
                )])

        buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="schedule_move")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await callback.message.edit_text("Выберите запись для переноса:", reply_markup=keyboard)
        await state.set_state(ScheduleState.move_select_schedule)
        await callback.answer()

    except Exception as e:
        logger.error(f"Error loading schedule: {e}")
        await callback.message.edit_text(f"Ошибка загрузки расписания: {e}")
        await callback.answer()

@router.callback_query(F.data.startswith("schedule_move_select_"))
async def schedule_move_select(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    schedule_id = int(parts[3])
    date_str = parts[4]

    await state.update_data(move_schedule_id=schedule_id, move_old_date=date_str)

    try:
        api_client = BackendAPIClient()

        schedule = await api_client.schedule_get_by_id(schedule_id, include_deleted=True)

        if not schedule:
            await callback.message.edit_text("Запись не найдена")
            await callback.answer()
            return

        if schedule.get('deleted_at'):
            await callback.message.edit_text("⚠️ Эта запись была удалена в составе серии")
            await callback.answer()
            return

        if schedule.get('is_recurring') and schedule.get('recurrence_group_id'):
            buttons = [
                [InlineKeyboardButton(text="📝 Только эту запись", callback_data="schedule_move_scope_current")],
                [InlineKeyboardButton(text="📋 Всю серию", callback_data="schedule_move_scope_series")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="schedule_move")]
            ]
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

            await callback.message.edit_text("Перенести только эту запись или всю серию?", reply_markup=keyboard)
            await state.set_state(ScheduleState.move_select_scope)
            await callback.answer()
        else:
            today = datetime.now()
            await state.update_data(calendar_year=today.year, calendar_month=today.month)

            user_data = await state.get_data()
            user_id = user_data.get("global_user_id")
            role = user_data.get("role", "specialist")

            busy_dates = await get_busy_dates_for_month(today.year, today.month, user_id if role == "specialist" else None)

            await callback.message.edit_text("Выберите новую дату:", reply_markup=get_calendar_keyboard(today.year, today.month, busy_dates))
            await state.set_state(ScheduleState.move_select_new_date)
            await callback.answer()

    except Exception as e:
        logger.error(f"Error selecting schedule for move: {e}")
        await callback.message.edit_text(f"Ошибка: {e}")
        await callback.answer()

async def schedule_delete_select_schedule(callback: CallbackQuery, state: FSMContext, date_str: str):
    user_data = await state.get_data()
    current_user_id = user_data.get("global_user_id")
    role = user_data.get("role", "specialist")

    try:
        api_client = BackendAPIClient()
        schedules = await api_client.schedule_get(date=date_str, user_id=current_user_id if role == "specialist" else None)

        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        formatted_date = date_obj.strftime("%d.%m.%Y")

        if not schedules:
            await callback.message.edit_text(f"На {formatted_date} нет записей")
            return

        buttons = []
        for sched in schedules:
            time_str = sched["start_time"][11:16]
            user_name = sched.get("user_name", "")
            if user_name:
                buttons.append([InlineKeyboardButton(
                    text=f"{time_str} - {sched['title']} ({user_name})",
                    callback_data=f"schedule_delete_select_{sched['id']}"
                )])
            else:
                buttons.append([InlineKeyboardButton(
                    text=f"{time_str} - {sched['title']}",
                    callback_data=f"schedule_delete_select_{sched['id']}"
                )])

        buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="schedule_delete")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await state.update_data(delete_selected_date=date_str)
        await callback.message.edit_text("Выберите запись для удаления:", reply_markup=keyboard)
        await state.set_state(ScheduleState.delete_select_schedule)
        await callback.answer()

    except Exception as e:
        logger.error(f"Error loading schedule: {e}")
        await callback.message.edit_text(f"Ошибка загрузки расписания: {e}")
        await callback.answer()

@router.callback_query(F.data.startswith("schedule_delete_select_"))
async def schedule_delete_select(callback: CallbackQuery, state: FSMContext):
    schedule_id = int(callback.data.split("_")[-1])

    try:
        api_client = BackendAPIClient()

        schedule = await api_client.schedule_get_by_id(schedule_id, include_deleted=True)

        if not schedule:
            await callback.message.edit_text("Запись не найдена")
            await callback.answer()
            return

        if schedule.get('deleted_at'):
            await callback.message.edit_text("⚠️ Эта запись была удалена в составе серии")
            await callback.answer()
            return

        await state.update_data(delete_schedule_id=schedule_id)

        if schedule.get('is_recurring') and schedule.get('recurrence_group_id'):
            buttons = [
                [InlineKeyboardButton(text="🗑️ Только эту запись", callback_data="schedule_delete_scope_current")],
                [InlineKeyboardButton(text="🗑️ Всю серию", callback_data="schedule_delete_scope_series")],
                [InlineKeyboardButton(text="❌ Отмена", callback_data="schedule_delete")]
            ]
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

            await callback.message.edit_text("Удалить только эту запись или всю серию?", reply_markup=keyboard)
            await state.set_state(ScheduleState.delete_select_scope)
            await callback.answer()
            return

        await state.update_data(delete_schedule_id=schedule_id)

        if schedule.get('is_recurring') and schedule.get('recurrence_group_id'):
            buttons = [
                [InlineKeyboardButton(text="🗑️ Только эту запись", callback_data="schedule_delete_scope_current")],
                [InlineKeyboardButton(text="🗑️ Всю серию", callback_data="schedule_delete_scope_series")],
                [InlineKeyboardButton(text="❌ Отмена", callback_data="schedule_delete")]
            ]
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

            await callback.message.edit_text("Удалить только эту запись или всю серию?", reply_markup=keyboard)
            await state.set_state(ScheduleState.delete_select_scope)
            await callback.answer()
        else:
            buttons = [
                [InlineKeyboardButton(text="✅ Да, удалить", callback_data="schedule_delete_confirm")],
                [InlineKeyboardButton(text="❌ Отмена", callback_data="schedule_delete")]
            ]
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

            await callback.message.edit_text("⚠️ Вы уверены, что хотите удалить эту запись?", reply_markup=keyboard)
            await state.set_state(ScheduleState.delete_confirm)
            await callback.answer()

    except Exception as e:
        logger.error(f"Error selecting schedule for delete: {e}")
        await callback.message.edit_text(f"Ошибка: {e}")
        await callback.answer()

@router.callback_query(F.data == "schedule_delete_confirm")
async def schedule_delete_confirm(callback: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    schedule_id = user_data.get("delete_schedule_id")

    try:
        api_client = BackendAPIClient()
        await api_client.schedule_delete(schedule_id)

        await callback.message.edit_text("✅ Запись успешно удалена")
        await callback.answer()
        await state.clear()
        await cmd_schedule(callback.message, state)

    except Exception as e:
        logger.error(f"Error deleting schedule: {e}")
        await callback.message.edit_text(f"Ошибка удаления записи: {e}")
        await callback.answer()

@router.callback_query(F.data.startswith("schedule_delete_scope_"))
async def schedule_delete_scope_selected(callback: CallbackQuery, state: FSMContext):
    scope = callback.data.split("_")[-1]
    user_data = await state.get_data()
    schedule_id = user_data.get("delete_schedule_id")

    try:
        api_client = BackendAPIClient()

        if scope == "series":
            schedule = await api_client.schedule_get_by_id(schedule_id, include_deleted=True)
            if schedule and schedule.get('recurrence_group_id'):
                from_date = user_data.get("delete_selected_date", datetime.now().strftime("%Y-%m-%d"))
                await api_client.schedule_delete_series(schedule['recurrence_group_id'], from_date=from_date)
                await callback.message.edit_text("✅ Вся серия записей успешно удалена!")
            else:
                await callback.message.edit_text("Ошибка: не удалось найти серию записей")
        else:
            buttons = [
                [InlineKeyboardButton(text="✅ Да, удалить", callback_data="schedule_delete_confirm")],
                [InlineKeyboardButton(text="❌ Отмена", callback_data="schedule_delete")]
            ]
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

            await callback.message.edit_text("⚠️ Вы уверены, что хотите удалить эту запись?", reply_markup=keyboard)
            await state.set_state(ScheduleState.delete_confirm)

        await callback.answer()
        if scope == "series":
            await state.clear()
            await cmd_schedule(callback.message, state)

    except Exception as e:
        logger.error(f"Error deleting schedule: {e}")
        await callback.message.edit_text(f"Ошибка удаления записи: {e}")
        await callback.answer()

@router.callback_query(F.data.startswith("schedule_create_client_idx_"))
async def schedule_create_client_selected(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.split("_")[-1])
    user_data = await state.get_data()
    client_names = user_data.get("create_client_names", [])
    if idx < len(client_names):
        client_name = client_names[idx]
        await state.update_data(create_client_name=client_name)

        buttons = [
            [InlineKeyboardButton(text="🔁 Повторять еженедельно", callback_data="schedule_create_recurrence_yes")],
            [InlineKeyboardButton(text="📅 Однократная запись", callback_data="schedule_create_recurrence_no")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="schedule_create")]
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await callback.message.edit_text(f"Создать повторяющуюся запись для {client_name}?", reply_markup=keyboard)
        await state.set_state(ScheduleState.create_select_recurrence)
        await callback.answer()
    else:
        await callback.answer("Ошибка выбора клиента")

@router.callback_query(F.data == "schedule_create_new_client")
async def schedule_create_new_client(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Введите имя нового клиента:")
    await state.set_state(ScheduleState.create_enter_name)
    await callback.answer()

@router.callback_query(F.data.startswith("schedule_create_recurrence_"))
async def schedule_create_recurrence_selected(callback: CallbackQuery, state: FSMContext):
    recurrence = callback.data.split("_")[-1]
    user_data = await state.get_data()

    user_id = user_data.get("global_user_id")
    client_name = user_data.get("create_client_name")
    date_str = user_data.get("create_date")
    time_str = user_data.get("create_time")

    try:
        api_client = BackendAPIClient()

        start_time = f"{date_str}T{time_str}:00"
        end_time_dt = datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%S") + timedelta(hours=1)
        end_time = end_time_dt.strftime("%Y-%m-%dT%H:%M:%S")

        if recurrence == "yes":
            await api_client.schedule_create_recurring(
                user_id=user_id,
                title=client_name,
                start_time=start_time,
                end_time=end_time
            )
            await callback.message.edit_text(f"✅ Создана повторяющаяся еженедельно запись для {client_name}!")
        else:
            await api_client.schedule_create(
                user_id=user_id,
                title=client_name,
                start_time=start_time,
                end_time=end_time
            )
            await callback.message.edit_text(f"✅ Запись успешно создана для {client_name}!")

        await callback.answer()
        await state.clear()
        await cmd_schedule(callback.message, state)

    except Exception as e:
        logger.error(f"Error creating schedule: {e}")
        await callback.message.edit_text(f"Ошибка создания записи: {e}")
        await callback.answer()

@router.callback_query(F.data.startswith("schedule_edit_scope_"))
async def schedule_edit_scope_selected(callback: CallbackQuery, state: FSMContext):
    scope = callback.data.split("_")[-1]

    if scope == "current":
        await callback.message.edit_text("Введите новое имя клиента:")
        await state.set_state(ScheduleState.edit_enter_name)
    elif scope == "series":
        await callback.message.edit_text("Введите новое имя клиента для всей серии:")
        await state.set_state(ScheduleState.edit_enter_name)
        await state.update_data(edit_scope="series")

    await callback.answer()

@router.callback_query(F.data.startswith("schedule_move_scope_"))
async def schedule_move_scope_selected(callback: CallbackQuery, state: FSMContext):
    scope = callback.data.split("_")[-1]

    if scope == "series":
        await state.update_data(move_scope="series")

    today = datetime.now()
    await state.update_data(calendar_year=today.year, calendar_month=today.month)

    user_data = await state.get_data()
    user_id = user_data.get("global_user_id")
    role = user_data.get("role", "specialist")

    busy_dates = await get_busy_dates_for_month(today.year, today.month, user_id if role == "specialist" else None)

    await callback.message.edit_text("Выберите новую дату:", reply_markup=get_calendar_keyboard(today.year, today.month, busy_dates))
    await state.set_state(ScheduleState.move_select_new_date)
    await callback.answer()

@router.callback_query(F.data.startswith("schedule_move_time_"))
async def schedule_move_time_selected(callback: CallbackQuery, state: FSMContext):
    time_str = callback.data.split("_")[-1]
    user_data = await state.get_data()
    schedule_id = user_data.get("move_schedule_id")
    date_str = user_data.get("move_new_date")
    move_scope = user_data.get("move_scope", "current")

    try:
        api_client = BackendAPIClient()

        start_time = f"{date_str}T{time_str}:00"
        end_time_dt = datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%S") + timedelta(hours=1)
        end_time = end_time_dt.strftime("%Y-%m-%dT%H:%M:%S")

        if move_scope == "series":
            schedule = await api_client.schedule_get_by_id(schedule_id, include_deleted=True)
            if schedule and schedule.get('recurrence_group_id'):
                from_date = datetime.now().strftime("%Y-%m-%d")
                await api_client.schedule_move_series(
                    schedule['recurrence_group_id'],
                    start_time,
                    end_time,
                    from_date=from_date
                )

                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                formatted_date = date_obj.strftime("%d.%m.%Y")

                await callback.message.edit_text(f"✅ Вся серия записей успешно перенесена!\n\n📅 Новая дата: {formatted_date}\n⏰ Новое время: {time_str}")
            else:
                await callback.message.edit_text("Ошибка: не удалось найти серию записей")
        else:
            await api_client.schedule_update(schedule_id, start_time=start_time, end_time=end_time)

            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            formatted_date = date_obj.strftime("%d.%m.%Y")

            await callback.message.edit_text(f"✅ Запись успешно перенесена!\n\n📅 Новая дата: {formatted_date}\n⏰ Новое время: {time_str}")

        await callback.answer()
        await state.clear()
        await cmd_schedule(callback.message, state)

    except Exception as e:
        logger.error(f"Error moving schedule: {e}")
        await callback.message.edit_text(f"Ошибка переноса записи: {e}")
