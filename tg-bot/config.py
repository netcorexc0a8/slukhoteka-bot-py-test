from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    BOT_TOKEN: str
    BACKEND_URL: str = "http://slukhoteka-backend:8000"
    ADMIN_USER_PH: str = ""
    START_HOUR: int = 0
    END_HOUR: int = 23
    TIME_SLOT_DURATION: int = 1
    COLOR_FREE: str = "🟩"
    COLOR_BUSY: str = "🟨"
    TIMEZONE: str = "Europe/Moscow"

    class Config:
        env_file = ".env"

    @property
    def admin_phones(self) -> List[str]:
        if not self.ADMIN_USER_PH:
            return []
        return [ph.strip() for ph in self.ADMIN_USER_PH.split(",") if ph.strip()]

settings = Settings()