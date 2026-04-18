import httpx
import os
from datetime import datetime, timedelta
from config import settings

class YandexDiskService:
    def __init__(self):
        self.token = settings.YANDEX_DISK_TOKEN
        self.file_name = settings.FILE_NAME
        self.base_url = "https://cloud-api.yandex.net/v1/disk/resources"

    def _get_file_path_with_date(self) -> str:
        now = datetime.now()
        month_year = now.strftime("%Y_%m")
        
        base_path = os.path.dirname(self.file_name)
        filename = os.path.basename(self.file_name)
        
        name, ext = os.path.splitext(filename)
        new_filename = f"{name}_{month_year}{ext}"
        
        if base_path:
            return f"{base_path}/{new_filename}"
        return new_filename

    async def upload_file(self, file_content: bytes) -> bool:
        try:
            file_path = self._get_file_path_with_date()
            async with httpx.AsyncClient() as client:
                headers = {"Authorization": f"OAuth {self.token}"}
                params = {"path": file_path, "overwrite": "true"}
                response = await client.get(
                    f"{self.base_url}/upload",
                    headers=headers,
                    params=params
                )
                response.raise_for_status()
                upload_url = response.json()["href"]

                response = await client.put(upload_url, content=file_content)
                response.raise_for_status()

                return True
        except Exception as e:
            print(f"Ошибка загрузки на Яндекс Диск: {e}")
            return False

    async def get_excel_from_backend(self, start_date: str, end_date: str, user_id: int = None, current_user_id: int = 0, current_user_role: str = "admin") -> bytes:
        try:
            async with httpx.AsyncClient() as client:
                params = {
                    "start_date": start_date,
                    "end_date": end_date,
                    "current_user_id": current_user_id,
                    "current_user_role": current_user_role
                }
                if user_id:
                    params["user_id"] = user_id
                response = await client.get(
                    f"{settings.BACKEND_URL}/api/v1/export/excel",
                    params=params
                )
                response.raise_for_status()
                return response.content
        except Exception as e:
            print(f"Ошибка получения Excel от Backend: {e}")
            return None
