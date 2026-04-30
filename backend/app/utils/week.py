from datetime import datetime, timedelta, timezone
from typing import Tuple


def iso_week_bounds(dt: datetime) -> Tuple[datetime, datetime]:
    """
    Возвращает (start_of_week, end_of_week) для ISO-недели, в которую попадает dt.

    ISO-неделя: понедельник 00:00:00 — следующий понедельник 00:00:00 (полуоткрытый интервал).
    Сохраняем tzinfo dt; если tzinfo нет — считаем UTC.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    monday = dt - timedelta(days=dt.weekday())
    monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)
    next_monday = monday + timedelta(days=7)
    return monday, next_monday


def iso_week_key(dt: datetime) -> str:
    """Строковый ключ ISO-недели вида '2026-W17' (для логов/сообщений)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    iso = dt.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"
