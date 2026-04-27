from datetime import datetime, timezone, timedelta
import os
import urllib.parse
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.crud.booking import get_bookings_in_range
from app.services.export_service import ExcelExportService
from app.models.user import GlobalUser, Role
from app.services.permission import has_permission, Permission
from app.config import settings

router = APIRouter()
excel_service = ExcelExportService()


@router.get("/excel")
def export_excel(
    start_date: str = Query(..., description="Начальная дата YYYY-MM-DD"),
    end_date: str = Query(..., description="Конечная дата YYYY-MM-DD"),
    user_id: Optional[int] = None,
    current_user_id: int = Query(..., description="ID текущего пользователя"),
    current_user_role: str = Query(..., description="Роль текущего пользователя"),
    db: Session = Depends(get_db),
):
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный формат даты. Используйте YYYY-MM-DD",
        )

    current_user = GlobalUser(id=current_user_id, role=Role(current_user_role))

    if not has_permission(current_user, Permission.EXPORT_ALL):
        if not has_permission(current_user, Permission.EXPORT_OWN):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="У вас нет прав для экспорта",
            )
        user_id = current_user_id

    bookings = get_bookings_in_range(db, start, end, specialist_id=user_id)
    excel_data = excel_service.export_schedule(bookings, current_user, db)

    month_year = start.strftime("%Y_%m")
    base_name = os.path.basename(settings.FILE_NAME)
    name, ext = os.path.splitext(base_name)
    filename = f"{name}_{month_year}{ext}"
    encoded_filename = urllib.parse.quote(filename)

    return Response(
        content=excel_data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"},
    )
