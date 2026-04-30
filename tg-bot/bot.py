from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from config import settings
from handlers import (
    auth, menu, schedule, subscriptions, groups, group_session, group_move,
    users, statistics, export, export_ics, sync, backup, help as help_handler,
)
from services.api_client import BackendAPIClient
from middlewares.auth_middleware import AuthMiddleware
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

bot = Bot(
    token=settings.BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher()

dp.message.middleware(AuthMiddleware())

api_client = BackendAPIClient()

dp.include_router(auth.router)
dp.include_router(menu.router)
dp.include_router(help_handler.router)
dp.include_router(users.router)
dp.include_router(statistics.router)
dp.include_router(export.router)
dp.include_router(export_ics.router)
dp.include_router(sync.router)
dp.include_router(backup.router)
# Subscriptions, groups, group_session ДО schedule:
# в schedule живёт общий calendar_callback, который переадресует
# нужные case'ы по строковому имени состояния.
dp.include_router(subscriptions.router)
dp.include_router(groups.router)
dp.include_router(group_session.router)
dp.include_router(group_move.router)
dp.include_router(schedule.router)

dp["api_client"] = api_client


async def main():
    logger.info("Starting Telegram bot...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
