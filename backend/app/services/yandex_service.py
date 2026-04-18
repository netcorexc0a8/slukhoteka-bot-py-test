import httpx
import os
from datetime import datetime
from app.config import settings

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

    async def upload_file(self, file_path: str, file_content: bytes) -> bool:
        try:
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

    async def download_file(self):
        try:
            file_path = self._get_file_path_with_date()
            async with httpx.AsyncClient() as client:
                headers = {"Authorization": f"OAuth {self.token}"}
                params = {"path": file_path}
                response = await client.get(
                    f"{self.base_url}/download",
                    headers=headers,
                    params=params
                )
                response.raise_for_status()
                download_url = response.json()["href"]

                response = await client.get(download_url)
                response.raise_for_status()

                return response.content
        except Exception as e:
            print(f"Ошибка скачивания с Яндекс Диска: {e}")
            return None
