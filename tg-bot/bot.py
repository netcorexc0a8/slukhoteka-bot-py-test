from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from config import settings
from handlers import (
    auth, menu, schedule, subscriptions,
    users, statistics, export, export_ics, sync, backup,
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

# Авторизация: middleware
dp.message.middleware(AuthMiddleware())

api_client = BackendAPIClient()

dp.include_router(auth.router)
dp.include_router(menu.router)
dp.include_router(users.router)
dp.include_router(statistics.router)
dp.include_router(export.router)
dp.include_router(export_ics.router)
dp.include_router(sync.router)
dp.include_router(backup.router)
# Subscriptions ДО schedule, потому что обрабатывает callback'и subs_*
# которые используются в т.ч. внутри потока создания записи в schedule.
dp.include_router(subscriptions.router)
dp.include_router(schedule.router)

dp["api_client"] = api_client


async def main():
    logger.info("Starting Telegram bot...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
