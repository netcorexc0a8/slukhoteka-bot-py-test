from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
import logging
from datetime import datetime

router = APIRouter()
logger = logging.getLogger(__name__)

# Список таблиц для бэкапа в порядке зависимостей (сначала родительские)
BACKUP_TABLES = [
    "global_users",
    "platform_users",
    "invite_codes",
    "clients",
    "services",
    "groups",
    "group_participants",
    "client_subscriptions",
    "bookings",
    "booking_specialists",
]


@router.get("/database")
async def backup_database(db: Session = Depends(get_db)):
    """Создаёт текстовый бэкап всех значимых таблиц в формате INSERT-ов."""
    try:
        backup_content = f"-- Database Backup - {datetime.now().isoformat()}\n\n"
        for table in BACKUP_TABLES:
            try:
                rows = db.execute(text(f"SELECT * FROM {table}")).fetchall()
            except Exception as table_err:
                # Таблица может не существовать (например, на этапе миграции) — пропускаем
                logger.warning(f"Skipping table {table}: {table_err}")
                continue
            backup_content += f"\n-- {table}\n"
            for row in rows:
                backup_content += f"INSERT INTO {table} VALUES {tuple(row)}\n"

        return Response(
            content=backup_content.encode("utf-8"),
            media_type="application/sql",
            headers={
                "Content-Disposition": (
                    f"attachment; filename=backup_"
                    f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
                )
            },
        )
    except Exception as e:
        logger.error(f"Error creating backup: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка создания резервной копии: {str(e)}",
        )
