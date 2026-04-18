from fastapi import APIRouter, Depends, HTTPException, status, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.yandex_service import YandexDiskService
from app.config import settings
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/yandex")
async def sync_to_yandex(
    file: UploadFile,
    db: Session = Depends(get_db)
):
    """
    Upload file to Yandex Disk
    """
    try:
        yandex_service = YandexDiskService()
        file_content = await file.read()

        result = await yandex_service.upload_file(yandex_service._get_file_path_with_date(), file_content)

        return {"success": True, "message": "Файл успешно загружен на Яндекс Диск"}

    except Exception as e:
        logger.error(f"Error syncing to Yandex Disk: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка синхронизации: {str(e)}"
        )
