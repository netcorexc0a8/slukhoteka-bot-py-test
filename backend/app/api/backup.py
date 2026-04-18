from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from app.config import settings
import logging
from datetime import datetime

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/database")
async def backup_database(db: Session = Depends(get_db)):
    """
    Create database backup
    """
    try:
        result = db.execute(text("SELECT * FROM global_users"))
        users_data = result.fetchall()

        result = db.execute(text("SELECT * FROM platform_users"))
        platform_users_data = result.fetchall()

        result = db.execute(text("SELECT * FROM schedules"))
        schedules_data = result.fetchall()

        result = db.execute(text("SELECT * FROM invite_codes"))
        invites_data = result.fetchall()

        backup_content = f"-- Database Backup - {datetime.now().isoformat()}\n\n"
        backup_content += "-- Global Users\n"
        for row in users_data:
            backup_content += f"INSERT INTO global_users VALUES {row}\n"

        backup_content += "\n-- Platform Users\n"
        for row in platform_users_data:
            backup_content += f"INSERT INTO platform_users VALUES {row}\n"

        backup_content += "\n-- Schedules\n"
        for row in schedules_data:
            backup_content += f"INSERT INTO schedules VALUES {row}\n"

        backup_content += "\n-- Invite Codes\n"
        for row in invites_data:
            backup_content += f"INSERT INTO invite_codes VALUES {row}\n"

        return Response(
            content=backup_content.encode('utf-8'),
            media_type="application/sql",
            headers={
                "Content-Disposition": f"attachment; filename=backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
            }
        )

    except Exception as e:
        logger.error(f"Error creating backup: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка создания резервной копии: {str(e)}"
        )
