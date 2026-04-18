#!/usr/bin/env python3
"""
Простой тестовый скрипт для VK бота на Python 3.13
Использует requests для взаимодействия с VK API
Токен указан в скрипте
"""

import requests
import time
import random
import json
from datetime import datetime, timedelta

# Главная клавиатура
MAIN_KEYBOARD = {
    "one_time": False,
    "inline": False,
    "buttons": [
        [
            {
                "action": {
                    "type": "text",
                    "label": "start",
                    "payload": json.dumps({"command": "start"})
                },
                "color": "primary"
            },
            {
                "action": {
                    "type": "text",
                    "label": "test",
                    "payload": json.dumps({"command": "test"})
                },
                "color": "secondary"
            }
        ],
        [
            {
                "action": {
                    "type": "text",
                    "label": "help",
                    "payload": json.dumps({"command": "help"})
                },
                "color": "positive"
            }
        ]
    ]
}

# Клавиатура с тестовыми кнопками
TEST_KEYBOARD = {
    "one_time": False,
    "inline": False,
    "buttons": [
        [
            {
                "action": {
                    "type": "text",
                    "label": "📅 Расписание",
                    "payload": json.dumps({"command": "test1"})
                },
                "color": "secondary"
            },
            {
                "action": {
                    "type": "text",
                    "label": "test2",
                    "payload": json.dumps({"command": "test2"})
                },
                "color": "secondary"
            }
        ],
        [
            {
                "action": {
                    "type": "text",
                    "label": "test3",
                    "payload": json.dumps({"command": "test3"})
                },
                "color": "secondary"
            },
            {
                "action": {
                    "type": "text",
                    "label": "test4",
                    "payload": json.dumps({"command": "test4"})
                },
                "color": "secondary"
            }
        ],
        [
            {
                "action": {
                    "type": "text",
                    "label": "back",
                    "payload": json.dumps({"command": "back"})
                },
                "color": "negative"
            }
        ]
    ]
}

# Inline клавиатура для тестовых сообщений
TEST_INLINE_KEYBOARD = {
    "one_time": False,
    "inline": True,
    "buttons": [
        [
            {
                "action": {
                    "type": "callback",
                    "label": "testinline1",
                    "payload": json.dumps({"command": "testinline1"})
                },
                "color": "primary"
            },
            {
                "action": {
                    "type": "callback",
                    "label": "testinline2",
                    "payload": json.dumps({"command": "testinline2"})
                },
                "color": "secondary"
            }
        ]
    ]
}

# Пустая клавиатура для удаления inline кнопок
EMPTY_KEYBOARD = {
    "buttons": []
}

# Токен VK бота (укажите свой токен)
VK_TOKEN = 'vk1.a.jH3HtbpIEDZoRcyeJxdCVjBLPdH6rzZauKrfwSdOBM3Hthie7eJ6F4hd-cSyHC3eqWkJIWUOGqmWlJ7iP0Ra4xG69d0q-76IQ7AlB_zACqC4cnSDf-Q2lJ4es6JxGwr5rSf6D95-HGrxjQ2ewcUGmAgatrRrn8Qs2W37iQYLdJiDm3Qyutz4PFtKP5Qd3nAmuPV2qYzL0ES48PRLjTs-kQ'

# ID группы (укажите свой group_id)
GROUP_ID = 237438163  # Замените на ваш group_id

# Версия API
API_VERSION = '5.199'

def get_long_poll_server():
    """Получение сервера для Long Poll"""
    url = 'https://api.vk.com/method/groups.getLongPollServer'
    params = {
        'group_id': GROUP_ID,
        'access_token': VK_TOKEN,
        'v': API_VERSION
    }
    response = requests.get(url, params=params)
    data = response.json()

    if 'response' in data:
        return data['response']
    else:
        return None

def send_message(peer_id, message, keyboard=None):
    """Отправка сообщения"""
    url = 'https://api.vk.com/method/messages.send'
    params = {
        'access_token': VK_TOKEN,
        'v': API_VERSION,
        'peer_id': peer_id,
        'message': message,
        'random_id': random.randint(1, 1000000)
    }
    if keyboard:
        params['keyboard'] = json.dumps(keyboard)
    response = requests.get(url, params=params)
    return response.json()

def edit_message(peer_id, conversation_message_id, message, keyboard=None):
    """Редактирование сообщения"""
    url = 'https://api.vk.com/method/messages.edit'
    params = {
        'access_token': VK_TOKEN,
        'v': API_VERSION,
        'peer_id': peer_id,
        'conversation_message_id': conversation_message_id,
        'message': message
    }
    if keyboard:
        params['keyboard'] = json.dumps(keyboard)
    response = requests.get(url, params=params)
    return response.json()

def get_message_id(peer_id, conversation_message_id):
    """Получение message_id по conversation_message_id"""
    url = 'https://api.vk.com/method/messages.getByConversationMessageId'
    params = {
        'access_token': VK_TOKEN,
        'v': API_VERSION,
        'peer_id': peer_id,
        'conversation_message_ids': conversation_message_id,
        'extended': 0
    }
    response = requests.get(url, params=params)
    data = response.json()

    if 'response' in data and 'items' in data['response'] and len(data['response']['items']) > 0:
        return data['response']['items'][0].get('id')
    return None

def delete_message(message_id, delete_for_all=False):
    """Удаление сообщения"""
    url = 'https://api.vk.com/method/messages.delete'
    params = {
        'access_token': VK_TOKEN,
        'v': API_VERSION,
        'message_ids': message_id,
        'delete_for_all': 1 if delete_for_all else 0
    }
    response = requests.get(url, params=params)
    return response.json()

def show_snackbar(event_id, user_id, peer_id, text):
    """Показать всплывающее сообщение для callback кнопки"""
    url = 'https://api.vk.com/method/messages.sendMessageEventAnswer'
    params = {
        'access_token': VK_TOKEN,
        'v': API_VERSION,
        'event_id': event_id,
        'user_id': user_id,
        'peer_id': peer_id,
        'event_data': json.dumps({"type": "show_snackbar", "text": text})
    }
    response = requests.get(url, params=params)
    return response.json()

# Хранилище для conversation_message_id сообщений с inline клавиатурой
inline_message_ids = {}

# Хранилище состояний календаря для пользователей
calendar_states = {}

MONTHS = [
    "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
]

def generate_month_keyboard(year_offset=0, month_offset=0):
    """Генерация inline клавиатуры для выбора месяца"""
    buttons = []
    current_year = datetime.now().year + year_offset
    current_month = datetime.now().month

    # Показываем только 6 месяцев (2 ряда по 3) из-за лимита 10 кнопок для inline
    start_month = month_offset * 6
    for i in range(start_month, min(start_month + 6, 12), 3):
        row = []
        for j in range(3):
            if i + j < 12:
                month_num = i + j + 1
                # Выделяем текущий месяц зеленым цветом
                color = "positive" if month_num == current_month and year_offset == 0 else "secondary"
                row.append({
                    "action": {
                        "type": "callback",
                        "label": MONTHS[i + j],
                        "payload": json.dumps({
                            "command": "select_month",
                            "month": month_num,
                            "year": current_year
                        })
                    },
                    "color": color
                })
        if row:
            buttons.append(row)

    # Пагинация и кнопка назад
    nav_row = []
    if month_offset > 0:
        nav_row.append({
            "action": {
                "type": "callback",
                "label": "◀️",
                "payload": json.dumps({
                    "command": "month_prev",
                    "year_offset": year_offset,
                    "month_offset": month_offset - 1
                })
            },
            "color": "secondary"
        })
    nav_row.append({
        "action": {
            "type": "callback",
            "label": "Назад",
            "payload": json.dumps({"command": "calendar_back"})
        },
        "color": "negative"
    })
    if start_month + 6 < 12:
        nav_row.append({
            "action": {
                "type": "callback",
                "label": "▶️",
                "payload": json.dumps({
                    "command": "month_next",
                    "year_offset": year_offset,
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

def generate_day_keyboard(month, year, day_offset=0):
    """Генерация inline клавиатуры для выбора дня месяца"""
    buttons = []

    # Вычисляем количество дней в месяце
    if month == 12:
        next_month = datetime(year + 1, 1, 1)
    else:
        next_month = datetime(year, month + 1, 1)
    days_in_month = (next_month - datetime(year, month, 1)).days

    # Текущая дата
    now = datetime.now()
    current_day = now.day
    current_month = now.month
    current_year = now.year

    # Показываем по 3 дня в ряду (лимит VK для inline - максимум 10 кнопок)
    start_day = day_offset * 6 + 1
    for week in range(2):
        row = []
        for day in range(3):
            current_day_number = start_day + week * 3 + day
            if current_day_number <= days_in_month:
                current_date = datetime(year, month, current_day_number)
                date_str = current_date.strftime("%d-%m-%Y")
                day_label = str(current_day_number)
                # Выделяем текущую дату зеленым цветом
                color = "positive" if current_day_number == current_day and month == current_month and year == current_year else "secondary"
                row.append({
                    "action": {
                        "type": "callback",
                        "label": day_label,
                        "payload": json.dumps({
                            "command": "select_date",
                            "date": date_str
                        })
                    },
                    "color": color
                })
        if row and start_day + week * 3 <= days_in_month:
            buttons.append(row)

    # Пагинация и кнопка назад
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
                "year_offset": year - datetime.now().year
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

def process_message(from_id, peer_id, text):
    """Обработка входящего сообщения"""
    print(f"Получено сообщение: {text}")

    keyboard = MAIN_KEYBOARD
    response = ""

    # Простой эхо-бот
    if text.lower() == 'start':
        response = "Привет!\nЯ тестовый бот «Слухотека»"
        keyboard = MAIN_KEYBOARD
    elif text.lower() == 'help':
        response = "Доступные команды:\nstart - приветствие\ntest - тестовые функции\nhelp - помощь"
        keyboard = MAIN_KEYBOARD
    elif text.lower() == 'test':
        response = "Выберите тест:"
        keyboard = TEST_KEYBOARD
    elif text.lower() == 'back':
        response = "Возврат в главное меню"
        keyboard = MAIN_KEYBOARD
    elif text.lower() == '📅 расписание' or text.lower() == 'test1':
        response = "Выберите месяц:"
        keyboard = generate_month_keyboard(0, 0)
    elif text.lower() == 'test2':
        response = "Тест 2 прошел успешно!"
        keyboard = TEST_INLINE_KEYBOARD
    elif text.lower() == 'test3':
        response = "Тест 3 прошел успешно!"
        keyboard = TEST_INLINE_KEYBOARD
    elif text.lower() == 'test4':
        response = "Тест 4 прошел успешно!"
        keyboard = TEST_INLINE_KEYBOARD
    elif text.lower() == 'testinline1':
        response = "Inline кнопка 1 нажата!"
        keyboard = TEST_KEYBOARD
    elif text.lower() == 'testinline2':
        response = "Inline кнопка 2 нажата!"
        keyboard = TEST_KEYBOARD
    else:
        response = f"Вы сказали: {text}"
        keyboard = MAIN_KEYBOARD

    # Отправляем ответ с клавиатурой
    result = send_message(peer_id, response, keyboard)

    # Если отправили сообщение с inline клавиатурой, сохраняем его ID
    if keyboard != MAIN_KEYBOARD and keyboard != TEST_KEYBOARD and 'response' in result:
        inline_message_ids[peer_id] = result['response']

def process_callback_event(peer_id, user_id, event_id, conversation_message_id, payload):
    """Обработка callback события от inline кнопки"""

    # Payload уже может быть словарем, если VK API его распарсил
    if isinstance(payload, str):
        payload_data = json.loads(payload)
        command = payload_data.get('command', '')
    else:
        payload_data = payload
        command = payload.get('command', '')

    delete_and_send_new = True
    response = ""
    keyboard = MAIN_KEYBOARD

    if command == 'testinline1':
        response = "Inline кнопка 1 нажата!"
        keyboard = TEST_KEYBOARD
    elif command == 'testinline2':
        response = "Inline кнопка 2 нажата!"
        keyboard = TEST_KEYBOARD
    elif command == 'select_month':
        month = payload_data.get('month', 1)
        year = payload_data.get('year', datetime.now().year)
        calendar_states[peer_id] = {'month': month, 'year': year, 'day_offset': 0}
        month_name = MONTHS[month - 1]
        response = f"Выберите день ({month_name} {year}):"
        keyboard = generate_day_keyboard(month, year, 0)
        delete_and_send_new = False
        edit_message(peer_id, conversation_message_id, response, keyboard)
        show_snackbar(event_id, user_id, peer_id, "✓ Месяц выбран")
        return
    elif command == 'month_prev':
        year_offset = payload_data.get('year_offset', 0)
        month_offset = payload_data.get('month_offset', 0)
        response = "Выберите месяц:"
        keyboard = generate_month_keyboard(year_offset, month_offset)
        delete_and_send_new = False
        edit_message(peer_id, conversation_message_id, response, keyboard)
        show_snackbar(event_id, user_id, peer_id, "✓ Предыдущие месяцы")
        return
    elif command == 'month_next':
        year_offset = payload_data.get('year_offset', 0)
        month_offset = payload_data.get('month_offset', 0)
        response = "Выберите месяц:"
        keyboard = generate_month_keyboard(year_offset, month_offset)
        delete_and_send_new = False
        edit_message(peer_id, conversation_message_id, response, keyboard)
        show_snackbar(event_id, user_id, peer_id, "✓ Следующие месяцы")
        return
    elif command == 'day_prev':
        month = payload_data.get('month', 1)
        year = payload_data.get('year', datetime.now().year)
        day_offset = payload_data.get('day_offset', 0)
        calendar_states[peer_id] = {'month': month, 'year': year, 'day_offset': day_offset}
        month_name = MONTHS[month - 1]
        response = f"Выберите день ({month_name} {year}):"
        keyboard = generate_day_keyboard(month, year, day_offset)
        delete_and_send_new = False
        edit_message(peer_id, conversation_message_id, response, keyboard)
        show_snackbar(event_id, user_id, peer_id, "✓ Предыдущие дни")
        return
    elif command == 'day_next':
        month = payload_data.get('month', 1)
        year = payload_data.get('year', datetime.now().year)
        day_offset = payload_data.get('day_offset', 0)
        calendar_states[peer_id] = {'month': month, 'year': year, 'day_offset': day_offset}
        month_name = MONTHS[month - 1]
        response = f"Выберите день ({month_name} {year}):"
        keyboard = generate_day_keyboard(month, year, day_offset)
        delete_and_send_new = False
        edit_message(peer_id, conversation_message_id, response, keyboard)
        show_snackbar(event_id, user_id, peer_id, "✓ Следующие дни")
        return
    elif command == 'select_date':
        date = payload_data.get('date', '')
        response = f"Выбранная дата: {date}"
    elif command == 'month_select':
        year_offset = payload_data.get('year_offset', 0)
        month_offset = 0
        response = "Выберите месяц:"
        keyboard = generate_month_keyboard(year_offset, month_offset)
    elif command == 'calendar_back':
        response = "Возврат в меню тестов"
        keyboard = TEST_KEYBOARD

    if delete_and_send_new:
        # Получаем message_id для удаления
        message_id = get_message_id(peer_id, conversation_message_id)

        # Удаляем сообщение с inline кнопками
        if message_id:
            delete_message(message_id, delete_for_all=True)

        # Удаляем из хранилища
        if peer_id in inline_message_ids:
            del inline_message_ids[peer_id]

        # Отправляем новое сообщение с результатом и клавиатурой
        send_message(peer_id, response, keyboard)
    else:
        # Удаляем из хранилища
        if peer_id in inline_message_ids:
            del inline_message_ids[peer_id]

        send_message(peer_id, response, keyboard)

    # Показываем всплывающее уведомление
    show_snackbar(event_id, user_id, peer_id, "✓ Готово")

def main():
    """Основной цикл бота"""
    print("Запуск тестового VK бота...")

    # Получаем Long Poll сервер
    server_info = get_long_poll_server()
    if not server_info:
        print("Не удалось получить Long Poll сервер")
        return

    server = server_info['server']
    key = server_info['key']
    ts = server_info['ts']

    print(f"Подключен к серверу")
    print("Ожидание сообщений... (Ctrl+C для выхода)")

    try:
        while True:
            # Запрос обновлений
            poll_url = f"{server}?act=a_check&key={key}&ts={ts}&wait=25"
            response = requests.get(poll_url, timeout=30)
            data = response.json()

            if 'failed' in data:
                if data['failed'] == 1:
                    ts = data['ts']
                else:
                    # Переподключение
                    print("Переподключение к Long Poll...")
                    server_info = get_long_poll_server()
                    if server_info:
                        server = server_info['server']
                        key = server_info['key']
                        ts = server_info['ts']
                    else:
                        print("Не удалось переподключиться")
                        break
                continue

            ts = data.get('ts', ts)

            # Обработка обновлений
            updates = data.get('updates', [])
            for update in updates:
                if update.get('type') == 'message_new':
                    message_data = update.get('object', {}).get('message', {})
                    from_id = message_data.get('from_id')
                    peer_id = message_data.get('peer_id')
                    text = message_data.get('text', '')

                    if text:
                        process_message(from_id, peer_id, text)
                elif update.get('type') == 'message_event':
                    event_data = update.get('object', {})
                    user_id = event_data.get('user_id')
                    peer_id = event_data.get('peer_id')
                    event_id = event_data.get('event_id')
                    conversation_message_id = event_data.get('conversation_message_id')
                    payload = event_data.get('payload')

                    process_callback_event(peer_id, user_id, event_id, conversation_message_id, payload)

            # Небольшая пауза
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nБот остановлен")
    except Exception as e:
        print(f"Ошибка: {e}")

if __name__ == '__main__':
    main()