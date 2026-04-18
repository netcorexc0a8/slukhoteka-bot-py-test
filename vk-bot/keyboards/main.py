import json
import re
from datetime import datetime

def normalize_phone(phone: str) -> str:
    phone = re.sub(r'[^\d+]', '', phone)
    if phone.startswith('8'):
        phone = '+7' + phone[1:]
    if phone.startswith('7') and not phone.startswith('+'):
        phone = '+' + phone
    if not re.match(r'^\+7\d{10}$', phone):
        raise ValueError(f"Неверный формат телефона: {phone}")
    return phone

def get_main_keyboard(role: str) -> dict:
    if role == "admin":
        buttons = [
            [{"action": {"type": "text", "label": "👤 Пользователи", "payload": json.dumps({"command": "users"})}, "color": "secondary"}],
            [{"action": {"type": "text", "label": "📅 Расписание", "payload": json.dumps({"command": "schedule"})}, "color": "primary"}],
            [{"action": {"type": "text", "label": "📊 Экспорт Excel", "payload": json.dumps({"command": "export"})}, "color": "secondary"}],
            [{"action": {"type": "text", "label": "❓ Помощь", "payload": json.dumps({"command": "help"})}, "color": "positive"}]
        ]
    elif role == "methodist":
        buttons = [
            [{"action": {"type": "text", "label": "👤 Пользователи", "payload": json.dumps({"command": "users"})}, "color": "secondary"}],
            [{"action": {"type": "text", "label": "📅 Расписание", "payload": json.dumps({"command": "schedule"})}, "color": "primary"}],
            [{"action": {"type": "text", "label": "📊 Экспорт Excel", "payload": json.dumps({"command": "export"})}, "color": "secondary"}],
            [{"action": {"type": "text", "label": "❓ Помощь", "payload": json.dumps({"command": "help"})}, "color": "positive"}]
        ]
    else:
        buttons = [
            [{"action": {"type": "text", "label": "📅 Расписание", "payload": json.dumps({"command": "schedule"})}, "color": "primary"}],
            [{"action": {"type": "text", "label": "📊 Экспорт Excel", "payload": json.dumps({"command": "export"})}, "color": "secondary"}],
            [{"action": {"type": "text", "label": "❓ Помощь", "payload": json.dumps({"command": "help"})}, "color": "positive"}]
        ]

    return {
        "one_time": False,
        "inline": False,
        "buttons": buttons
    }

def get_month_keyboard(year: int, month: int, month_offset: int = 0) -> dict:
    buttons = []
    today = datetime.now()

    MONTHS = [
        "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
    ]

    start_month = month_offset * 3
    for i in range(start_month, min(start_month + 3, 12)):
        month_num = i + 1
        is_current = month_num == today.month and year == today.year
        color = "positive" if is_current else "secondary"

        buttons.append([{
            "action": {
                "type": "callback",
                "label": MONTHS[i],
                "payload": json.dumps({
                    "command": "select_month",
                    "month": month_num,
                    "year": year
                })
            },
            "color": color
        }])

    nav_row = []
    if month_offset > 0:
        nav_row.append({
            "action": {
                "type": "callback",
                "label": "◀️",
                "payload": json.dumps({
                    "command": "month_prev",
                    "year": year,
                    "month_offset": month_offset - 1
                })
            },
            "color": "secondary"
        })

    nav_row.append({
        "action": {
            "type": "callback",
            "label": "Отмена",
            "payload": json.dumps({"command": "calendar_cancel"})
        },
        "color": "negative"
    })

    if start_month + 3 < 12:
        nav_row.append({
            "action": {
                "type": "callback",
                "label": "▶️",
                "payload": json.dumps({
                    "command": "month_next",
                    "year": year,
                    "month_offset": month_offset + 1
                })
            },
            "color": "secondary"
        })

    buttons.append(nav_row)

    return {
        "one_time": False,
        "inline": True,
        "buttons": buttons
    }

def get_day_keyboard(year: int, month: int, day_offset: int = 0) -> dict:
    buttons = []
    today = datetime.now()

    if month == 12:
        next_month = datetime(year + 1, 1, 1)
    else:
        next_month = datetime(year, month + 1, 1)
    days_in_month = (next_month - datetime(year, month, 1)).days

    start_day = day_offset * 6 + 1
    for week in range(2):
        row = []
        for day in range(3):
            current_day_number = start_day + week * 3 + day
            if current_day_number <= days_in_month:
                current_date = datetime(year, month, current_day_number)
                is_today = current_date.date() == today.date()
                is_past = current_date.date() < today.date()

                button_text = str(current_day_number)
                if is_today:
                    button_text = f"🔴{current_day_number}"
                elif is_past:
                    button_text = f"⚪{current_day_number}"

                color = "positive" if is_today else "secondary"

                row.append({
                    "action": {
                        "type": "callback",
                        "label": button_text,
                        "payload": json.dumps({
                            "command": "select_day",
                            "date": current_date.strftime("%d-%m-%Y")
                        })
                    },
                    "color": color
                })
        if row and start_day + week * 3 <= days_in_month:
            buttons.append(row)

    nav_row = []
    if day_offset > 0:
        nav_row.append({
            "action": {
                "type": "callback",
                "label": "◀️",
                "payload": json.dumps({
                    "command": "day_prev",
                    "month": month,
                    "year": year,
                    "day_offset": day_offset - 1
                })
            },
            "color": "secondary"
        })

    nav_row.append({
        "action": {
            "type": "callback",
            "label": "Назад",
            "payload": json.dumps({
                "command": "month_select",
                "year": year,
                "month_offset": 0
            })
        },
        "color": "negative"
    })

    if start_day + 6 <= days_in_month:
        nav_row.append({
            "action": {
                "type": "callback",
                "label": "▶️",
                "payload": json.dumps({
                    "command": "day_next",
                    "month": month,
                    "year": year,
                    "day_offset": day_offset + 1
                })
            },
            "color": "secondary"
        })

    buttons.append(nav_row)

    return {
        "one_time": False,
        "inline": True,
        "buttons": buttons
    }
