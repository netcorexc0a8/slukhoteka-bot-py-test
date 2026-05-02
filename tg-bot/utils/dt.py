"""
Утилиты для работы с датой и временем.

Все datetime.now() в проекте должны использовать now() из этого модуля,
чтобы учитывать часовой пояс из конфига (TIMEZONE, по умолчанию Europe/Moscow).
"""
from datetime import datetime
from zoneinfo import ZoneInfo
from config import settings


def now() -> datetime:
    """Текущее время в часовом поясе из настроек."""
    return datetime.now(tz=ZoneInfo(settings.TIMEZONE))


def tz() -> ZoneInfo:
    """Объект часового пояса из настроек."""
    return ZoneInfo(settings.TIMEZONE)