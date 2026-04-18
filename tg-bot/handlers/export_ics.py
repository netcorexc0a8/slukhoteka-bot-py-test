from aiogram import Router, F
from aiogram.types import Message, BufferedInputFile
from aiogram.fsm.context import FSMContext
from services.api_client import BackendAPIClient
from datetime import datetime, timedelta
import logging

router = Router()
logger = logging.getLogger(__name__)

@router.message(F.text == "📅 Экспорт ICS")
async def cmd_export_ics(message: Message, state: FSMContext):
    data = await state.get_data()
    role = data.get("role", "specialist")

    if role != "admin":
        await message.answer("У вас нет прав для экспорта ICS")
        from handlers.menu import show_main_menu
        await show_main_menu(message, state)
        return

    try:
        api_client = BackendAPIClient()
        current_user_id = data.get("global_user_id")

        today = datetime.now()
        first_day = today.replace(day=1)
        last_day = (first_day + timedelta(days=32)).replace(day=1) - timedelta(days=1)

        start_date = first_day.strftime("%Y-%m-%d")
        end_date = last_day.strftime("%Y-%m-%d")

        schedules = await api_client.schedule_get_all(start_date, end_date)

        if not schedules:
            await message.answer("Нет данных для экспорта ICS")
            return

        ics_content = generate_ics(schedules)

        file = BufferedInputFile(
            file=ics_content.encode('utf-8'),
            filename=f"schedule_{start_date}_{end_date}.ics"
        )

        await message.answer_document(
            document=file,
            caption=f"📅 ICS файл за {first_day.strftime('%B %Y')}"
        )

    except Exception as e:
        logger.error(f"Error exporting ICS: {e}")
        await message.answer(f"Ошибка экспорта ICS: {e}")

def generate_ics(schedules):
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Slukhoteka//Schedule//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Слухотека",
        "X-WR-TIMEZONE:Europe/Moscow",
        "X-WR-CALDESC:Расписание записи клиентов"
    ]

    for sched in schedules:
        start_time = sched["start_time"].replace("-", "").replace(":", "").replace("T", "")
        end_time = sched["end_time"].replace("-", "").replace(":", "").replace("T", "")

        lines.extend([
            "BEGIN:VEVENT",
            f"DTSTART:{start_time}",
            f"DTEND:{end_time}",
            f"SUMMARY:{sched['title']}",
            f"DESCRIPTION:Запись клиента",
            "END:VEVENT"
        ])

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)
