import json
from datetime import datetime
from services.api_client import BackendAPIClient
from services.vk_api import VKAPIClient
from keyboards.main import get_main_keyboard, get_month_keyboard, get_day_keyboard, normalize_phone

api_client = BackendAPIClient()
user_states = {}

async def process_message(from_id: int, peer_id: int, text: str, vk_api: VKAPIClient):
    user_id_str = str(from_id)

    if text.lower() == "start" or user_id_str not in user_states:
        user_states[user_id_str] = {"state": "waiting_for_phone"}

        user_info = vk_api.get_user_info(from_id)
        if user_info and "phone" in user_info and user_info["phone"]:
            phone = user_info["phone"]
            try:
                phone = normalize_phone(phone)
                result = api_client.auth_login(
                    phone=phone,
                    platform="vk",
                    external_id=str(from_id)
                )

                user_states[user_id_str] = {
                    "state": "authorized",
                    "global_user_id": result["global_user_id"],
                    "role": result["role"],
                    "platform_user_id": result["platform_user_id"],
                    "phone": phone
                }

                user_name = result.get("name") or user_info.get("first_name", "")
                if not result.get("name") and user_info.get("last_name"):
                    user_name += f" {user_info['last_name']}"

                role_display = result['role'].capitalize()
                if role_display == 'Specialist':
                    role_display = 'Специалист'
                elif role_display == 'Admin':
                    role_display = 'Администратор'
                elif role_display == 'Methodist':
                    role_display = 'Методист'

                keyboard = get_main_keyboard(result["role"])
                vk_api.send_message(
                    peer_id,
                    f"👋 Привет, {user_name}!\n\n"
                    f"Добро пожаловать в систему управления расписанием специалистов \"Слухотека\"\n\n"
                    f"🎭 Ваша роль: {role_display}\n\n"
                    f"Выберите действие в меню:",
                    keyboard=keyboard
                )
                return
            except Exception as e:
                vk_api.send_message(peer_id, f"Не удалось авторизоваться с номером из VK: {e}")

        vk_api.send_message(peer_id, "Добро пожаловать в систему управления расписанием специалистов \"Слухотека\"!\n\nК сожалению, не удалось получить ваш номер телефона из VK автоматически.\nПожалуйста, введите ваш номер телефона в формате +7XXXXXXXXXX")
        return

    user_state = user_states[user_id_str]
    state = user_state.get("state")

    if state == "waiting_for_phone":
        try:
            phone = normalize_phone(text)
            result = api_client.auth_login(
                phone=phone,
                platform="vk",
                external_id=str(from_id)
            )

            user_states[user_id_str] = {
                "state": "authorized",
                "global_user_id": result["global_user_id"],
                "role": result["role"],
                "platform_user_id": result["platform_user_id"],
                "phone": phone
            }

            user_info = vk_api.get_user_info(from_id)
            user_name = result.get("name") or (user_info.get("first_name", "") if user_info else "")
            if not result.get("name") and user_info and user_info.get("last_name"):
                user_name += f" {user_info['last_name']}"

            role_display = result['role'].capitalize()
            if role_display == 'Specialist':
                role_display = 'Специалист'
            elif role_display == 'Admin':
                role_display = 'Администратор'
            elif role_display == 'Methodist':
                role_display = 'Методист'

            keyboard = get_main_keyboard(result["role"])
            vk_api.send_message(
                peer_id,
                f"👋 Привет, {user_name}!\n\n"
                f"Добро пожаловать в систему управления расписанием специалистов \"Слухотека\"\n\n"
                f"🎭 Ваша роль: {role_display}\n\n"
                f"Выберите действие в меню:",
                keyboard=keyboard
            )
        except Exception as e:
            vk_api.send_message(peer_id, f"Ошибка авторизации: {e}")

    elif state == "authorized":
        try:
            payload_data = json.loads(text) if text.startswith("{") else None
            command = payload_data.get("command") if payload_data else text

            if command == "help":
                vk_api.send_message(peer_id, "📖 Справка по системе Слухотека\n\nРасписание: просмотр, создание, изменение записей\nЭкспорт Excel: выгрузка данных\n\nДля работы с расписанием выберите соответствующий пункт в меню.")

            elif command == "export":
                import os
                from config import settings
                
                today = datetime.now()
                first_day = today.replace(day=1)
                month_year = first_day.strftime("%Y_%m")
                
                base_path = os.path.dirname(settings.FILE_NAME)
                filename = os.path.basename(settings.FILE_NAME)
                name, ext = os.path.splitext(filename)
                new_filename = f"{name}_{month_year}{ext}"
                
                if base_path:
                    full_path = f"{base_path}/{new_filename}"
                else:
                    full_path = new_filename
                
                vk_api.send_message(peer_id, f"📊 Экспорт Excel за {first_day.strftime('%B %Y')} запущен.\n\nФайл будет доступен на Яндекс Диске: {full_path}\n\nИли воспользуйтесь Telegram ботом для получения файла напрямую.")

            elif command == "schedule":
                today = datetime.now()
                user_states[user_id_str]["calendar_state"] = {"year": today.year, "month": today.month, "month_offset": 0}
                calendar_kb = get_month_keyboard(today.year, today.month, 0)
                vk_api.send_message(peer_id, "Выберите месяц:", keyboard=calendar_kb)
                user_states[user_id_str]["state"] = "schedule_selecting_month"

        except Exception as e:
            vk_api.send_message(peer_id, f"Ошибка: {e}")

async def process_callback(peer_id: int, user_id: int, event_id: int, conversation_message_id: int, payload: str, vk_api: VKAPIClient):
    user_id_str = str(user_id)

    if user_id_str not in user_states:
        vk_api.show_snackbar(event_id, user_id, peer_id, "Сначала авторизуйтесь")
        return

    try:
        if isinstance(payload, str):
            payload_data = json.loads(payload)
        else:
            payload_data = payload

        command = payload_data.get("command", "")

        if command == "select_month":
            month = payload_data.get("month", 1)
            year = payload_data.get("year", datetime.now().year)
            user_states[user_id_str]["calendar_state"] = {"month": month, "year": year, "day_offset": 0}
            day_kb = get_day_keyboard(year, month, 0)
            vk_api.edit_message(peer_id, conversation_message_id, f"Выберите день ({month}.{year}):", day_kb)
            vk_api.show_snackbar(event_id, user_id, peer_id, "✓ Месяц выбран")

        elif command == "select_day":
            date = payload_data.get("date", "")
            user_data = user_states[user_id_str]
            user_id_num = user_data.get("global_user_id")
            role = user_data.get("role", "specialist")

            try:
                schedules = api_client.schedule_get(date=date, user_id=user_id_num if role == "specialist" else None)

                if not schedules:
                    vk_api.edit_message(peer_id, conversation_message_id, f"На {date} нет записей", None)
                    user_states[user_id_str]["state"] = "authorized"
                else:
                    response_text = f"📅 Записи на {date}:\n\n"
                    for sched in schedules:
                        time_str = sched["start_time"][11:16]
                        user_name = sched.get("user_name", "")
                        if user_name:
                            response_text += f"• {time_str} - {sched['title']} ({user_name})\n"
                        else:
                            response_text += f"• {time_str} - {sched['title']}\n"
                    vk_api.edit_message(peer_id, conversation_message_id, response_text, None)
                    user_states[user_id_str]["state"] = "authorized"
            except Exception as e:
                vk_api.edit_message(peer_id, conversation_message_id, f"Ошибка: {e}", None)

        elif command == "calendar_cancel":
            keyboard = get_main_keyboard(user_states[user_id_str].get("role", "specialist"))
            vk_api.edit_message(peer_id, conversation_message_id, "Главное меню:", keyboard)
            user_states[user_id_str]["state"] = "authorized"

        elif command in ["month_prev", "month_next", "day_prev", "day_next"]:
            calendar_state = user_states[user_id_str].get("calendar_state", {})
            month = calendar_state.get("month", datetime.now().month)
            year = calendar_state.get("year", datetime.now().year)

            if command in ["month_prev", "month_next"]:
                month_offset = payload_data.get("month_offset", 0)
                calendar_kb = get_month_keyboard(year, month, month_offset)
                vk_api.edit_message(peer_id, conversation_message_id, "Выберите месяц:", calendar_kb)
                user_states[user_id_str]["calendar_state"]["month_offset"] = month_offset
            else:
                day_offset = payload_data.get("day_offset", 0)
                day_kb = get_day_keyboard(year, month, day_offset)
                vk_api.edit_message(peer_id, conversation_message_id, f"Выберите день ({month}.{year}):", day_kb)
                user_states[user_id_str]["calendar_state"]["day_offset"] = day_offset

        vk_api.show_snackbar(event_id, user_id, peer_id, "✓")

    except Exception as e:
        vk_api.show_snackbar(event_id, user_id, peer_id, f"Ошибка: {e}")
