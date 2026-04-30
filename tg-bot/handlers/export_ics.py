from aiogram import Router, F
from aiogram.types import Message, BufferedInputFile
from aiogram.fsm.context import FSMContext
from services.api_client import BackendAPIClient
from datetime import datetime, timedelta
import logging

router = Router()
logger = logging.getLogger(__name__)


@router.message(F.text.in_(["📅 Экспорт ICS", "📆 Экспорт ICS"]))
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

        today = datetime.now()
        first_day = today.replace(day=1)
        last_day = (first_day + timedelta(days=32)).replace(day=1) - timedelta(days=1)

        start_date = first_day.strftime("%Y-%m-%d")
        end_date = last_day.strftime("%Y-%m-%d")

        bookings = await api_client.bookings_for_range(start_date, end_date)
        # Не выгружаем удалённые/отменённые
        bookings = [
            b for b in bookings
            if not b.get("deleted_at")
            and b.get("status") not in ("cancelled", "specialist_cancelled")
        ]

        if not bookings:
            await message.answer("Нет данных для экспорта ICS")
            return

        ics_content = generate_ics(bookings)

        file = BufferedInputFile(
            file=ics_content.encode("utf-8"),
            filename=f"schedule_{start_date}_{end_date}.ics",
        )

        await message.answer_document(
            document=file,
            caption=f"📅 ICS файл за {first_day.strftime('%B %Y')}",
        )

    except Exception as e:
        logger.error(f"Error exporting ICS: {e}")
        await message.answer(f"Ошибка экспорта ICS: {e}")


def _ics_escape(s: str) -> str:
    """Базовый escape для ICS-полей."""
    if s is None:
        return ""
    return s.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;").replace("\n", "\\n")


def generate_ics(bookings):
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Slukhoteka//Schedule//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Слухотека",
        "X-WR-TIMEZONE:Europe/Moscow",
        "X-WR-CALDESC:Расписание записи клиентов",
    ]

    for b in bookings:
        # ISO → 20260427T100000 (без TZ — клиенты обычно интерпретируют как локальное)
        start_time = b["start_time"].replace("-", "").replace(":", "").replace("T", "")
        end_time = b["end_time"].replace("-", "").replace(":", "").replace("T", "")
        # Срезаем возможный +00:00 / Z в хвосте
        if "+" in start_time:
            start_time = start_time.split("+")[0]
        if "+" in end_time:
            end_time = end_time.split("+")[0]
        start_time = start_time.rstrip("Z")[:15]
        end_time = end_time.rstrip("Z")[:15]

        client_name = b.get("client_name") or "Запись"
        specialist = b.get("specialist_name") or ""
        service = b.get("service_name") or ""

        summary = client_name
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
            f"SUMMARY:{_ics_escape(summary)}",
            f"DESCRIPTION:{_ics_escape(description)}",
            "END:VEVENT",
        ])

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)
