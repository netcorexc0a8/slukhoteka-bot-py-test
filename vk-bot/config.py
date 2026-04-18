from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    VK_BOT_TOKEN: str
    VK_GROUP_ID: int
    BACKEND_URL: str = "http://slukhoteka-backend:8000"
    FILE_NAME: str = "/Slukhoteka/Расписание.xlsx"
    START_HOUR: int = 0
    END_HOUR: int = 23
    TIME_SLOT_DURATION: int = 1
    COLOR_FREE: str = "🟩"
    COLOR_BUSY: str = "🟨"

    class Config:
        env_file = ".env"

settings = Settings()
