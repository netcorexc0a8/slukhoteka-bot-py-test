from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    DATABASE_URL: str
    ADMIN_USER_PH: str = ""
    YANDEX_DISK_TOKEN: str = ""
    FILE_NAME: str = "/Slukhoteka/Расписание.xlsx"
    SYNC_INTERVAL: int = 120
    START_HOUR: int = 0
    END_HOUR: int = 23
    TIME_SLOT_DURATION: int = 1
    COLOR_FREE: str = "🟩"
    COLOR_BUSY: str = "🟨"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def admin_phones(self) -> List[str]:
        if not self.ADMIN_USER_PH:
            return []
        return [ph.strip() for ph in self.ADMIN_USER_PH.split(",") if ph.strip()]

settings = Settings()
