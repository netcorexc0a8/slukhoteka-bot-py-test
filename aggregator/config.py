from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    BACKEND_URL: str = "http://slukhoteka-backend:8000"
    YANDEX_DISK_TOKEN: str = ""
    FILE_NAME: str = "/Slukhoteka/Расписание.xlsx"
    SYNC_INTERVAL: int = 120

    class Config:
        env_file = ".env"

settings = Settings()
