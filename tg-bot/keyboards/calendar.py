from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
from config import settings

def get_calendar_keyboard(year: int, month: int, busy_dates=None) -> InlineKeyboardMarkup:
    if busy_dates is None:
        busy_dates = []
    keyboard = []

    month_names = [
        "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
    ]

    nav_row = []
    if month > 1:
        nav_row.append(InlineKeyboardButton(
            text="◀️",
            callback_data=f"calendar_prev_month"
        ))

    nav_row.append(InlineKeyboardButton(
        text=f"{month_names[month-1]} {year}",
        callback_data="calendar_ignore"
    ))

    if month < 12:
        nav_row.append(InlineKeyboardButton(
            text="▶️",
            callback_data=f"calendar_next_month"
        ))

    keyboard.append(nav_row)

    days_row = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    keyboard.append([
        InlineKeyboardButton(text=day, callback_data="calendar_ignore")
        for day in days_row
    ])

    first_day = datetime(year, month, 1)
    if month == 12:
        last_day = datetime(year + 1, 1, 1)
    else:
        last_day = datetime(year, month + 1, 1)

    days_in_month = (last_day - first_day).days
    first_weekday = first_day.weekday()

    week_row = []
    for _ in range(first_weekday):
        week_row.append(InlineKeyboardButton(text=" ", callback_data="calendar_ignore"))

    for day in range(1, days_in_month + 1):
        current_date = datetime(year, month, day)
        date_str = current_date.strftime("%Y-%m-%d")
        is_busy = date_str in busy_dates

        if is_busy:
            color = settings.COLOR_BUSY
        else:
            color = settings.COLOR_FREE

        if day < 10:
            button_text = f"{color} {day}"
        else:
            button_text = f"{color}{day}"

        week_row.append(InlineKeyboardButton(
            text=button_text,
            callback_data=f"calendar_day_{year:04d}_{month:02d}_{day:02d}"
        ))

        if len(week_row) == 7:
            keyboard.append(week_row)
            week_row = []

    if week_row:
        while len(week_row) < 7:
            week_row.append(InlineKeyboardButton(text="  ", callback_data="calendar_ignore"))
        keyboard.append(week_row)

    keyboard.append([
        InlineKeyboardButton(text="❌ Отмена", callback_data="calendar_cancel")
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)
