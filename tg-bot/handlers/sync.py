from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from services.api_client import BackendAPIClient
import logging
from datetime import datetime, timedelta
from utils.dt import now as dt_now

router = Router()
logger = logging.getLogger(__name__)

@router.message(F.text.in_(["🔄 Синхронизация", "☁️ Синхр. Я.Диск"]))
async def cmd_sync(message: Message, state: FSMContext):
    data = await state.get_data()
    role = data.get("role", "specialist")

    if role not in ["admin", "methodist", "specialist"]:
        await message.answer("У вас нет прав для синхронизации")
        from handlers.menu import show_main_menu
        await show_main_menu(message, state)
        return

    try:
        api_client = BackendAPIClient()

        await message.answer("🔄 Начинаю синхронизацию с Яндекс Диск...")

        current_user_id = data.get("global_user_id")
        current_user_role = data.get("role", "specialist")

        today = dt_now()
        first_day = today.replace(day=1)
        last_day = (first_day + timedelta(days=32)).replace(day=1) - timedelta(days=1)

        start_date = first_day.strftime("%Y-%m-%d")
        end_date = last_day.strftime("%Y-%m-%d")
        month_year = first_day.strftime("%Y_%m")

        if current_user_role == "specialist":
            excel_data = await api_client.export_excel(start_date, end_date, current_user_id, current_user_id, current_user_role)
        else:
            excel_data = await api_client.export_excel(start_date, end_date, None, current_user_id, current_user_role)

        if not excel_data:
            await message.answer("Нет данных для синхронизации")
            return

        await api_client.sync_to_yandex(excel_data, f"schedule_{month_year}.xlsx")

        await message.answer(f"✅ Синхронизация успешно завершена!\n\n📅 Период: {first_day.strftime('%B %Y')}\n📁 Файл загружен на Яндекс Диск")

    except Exception as e:
        logger.error(f"Error syncing to Yandex Disk: {e}")
        await message.answer(f"Ошибка синхронизации: {e}")