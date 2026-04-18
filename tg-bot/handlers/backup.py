from aiogram import Router, F
from aiogram.types import Message, BufferedInputFile
from aiogram.fsm.context import FSMContext
from services.api_client import BackendAPIClient
import logging
from datetime import datetime

router = Router()
logger = logging.getLogger(__name__)

@router.message(F.text == "💾 Резервная копия БД")
async def cmd_backup(message: Message, state: FSMContext):
    data = await state.get_data()
    role = data.get("role", "specialist")

    if role != "admin":
        await message.answer("У вас нет прав для создания резервной копии")
        from handlers.menu import show_main_menu
        await show_main_menu(message, state)
        return

    try:
        api_client = BackendAPIClient()

        await message.answer("💾 Создаю резервную копию базы данных...")

        backup_data = await api_client.backup_database()

        if not backup_data:
            await message.answer("Ошибка создания резервной копии")
            return

        file = BufferedInputFile(
            file=backup_data,
            filename=f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
        )

        await message.answer_document(
            document=file,
            caption=f"💾 Резервная копия базы данных от {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )

    except Exception as e:
        logger.error(f"Error creating backup: {e}")
        await message.answer(f"Ошибка создания резервной копии: {e}")
