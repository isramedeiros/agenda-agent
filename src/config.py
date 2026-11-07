from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    TIMEZONE: str = "America/Sao_Paulo"
    CRON_HOUR: int = 6
    CRON_MINUTE: int = 30
    DESTINATION_PHONE: str = ""
    GEMINI_API_KEY: str = ""
    GOOGLE_SERVICE_ACCOUNT_FILE: str = "/app/credentials/service_account.json"
    GOOGLE_CALENDAR_ID: str = "primary"
    GOOGLE_CALENDAR_ICS_URL: str = ""
    EVOLUTION_BASE_URL: str = "http://evolution-api:8080"
    EVOLUTION_API_KEY: str = "secure_token"
    INSTANCE_NAME: str = "agenda-notifier"

    class Config:
        env_file = ".env"
        extra = "ignore"

@lru_cache
def get_settings() -> Settings:
    return Settings()
