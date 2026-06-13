from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """ Application Settings """
    APP_NAME: str = "Atlas"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    DATABASE_URL: Optional[str] = None
    DB_ECHO: bool = False

    REDIS_URL: Optional[str] = None

    # KITE API Settings
    KITE_API_KEY: Optional[str] = None
    KITE_API_SECRET: Optional[str] = None
    KITE_LOGIN_ID: Optional[str] = None
    KITE_PASSWORD: Optional[str] = None
    KITE_TOTP_SECRET: Optional[str] = None

    # SMTP Settings
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: Optional[int] = None
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

settings = Settings()
