import asyncio
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from services.yandex_service import YandexDiskService
from config import settings

yandex_service = YandexDiskService()
scheduler = AsyncIOScheduler()

async def sync_to_yandex():
    now = datetime.now()
    start_date = (now.replace(day=1)).strftime("%Y-%m-%d")
    end_date = (now.replace(day=1) + timedelta(days=32)).replace(day=1).strftime("%Y-%m-%d")

    print(f"Синхронизация с Яндекс Диск: {start_date} - {end_date}")

    excel_content = await yandex_service.get_excel_from_backend(
        start_date=start_date,
        end_date=end_date,
        current_user_id=1,
        current_user_role="admin"
    )

    if excel_content:
        success = await yandex_service.upload_file(excel_content)
        if success:
            print("Синхронизация завершена успешно")
        else:
            print("Ошибка при загрузке файла")
    else:
        print("Ошибка при получении Excel от Backend")


def start_scheduler():
    scheduler.add_job(
        sync_to_yandex,
        'interval',
        seconds=settings.SYNC_INTERVAL,
        id='sync_yandex'
    )
    scheduler.start()
    print("Планировщик задач запущен")
    print(f"Полная синхронизация каждые {settings.SYNC_INTERVAL} сек")
