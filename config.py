"""
Application configuration settings, loaded from environment variables.
"""

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional, Union
from datetime import time
from loguru import logger

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', case_sensitive=False, extra='ignore')

    # Environment
    environment: str = Field('development', env='ENVIRONMENT')

    # Database
    DATABASE_URL: str = Field(..., env='DATABASE_URL')
    REDIS_URL: str = Field(..., env='REDIS_URL')

    # Kite API
    KITE_API_KEY: str = Field(..., env='KITE_API_KEY')
    KITE_API_SECRET: str = Field(..., env='KITE_API_SECRET')
    KITE_TOTP_SECRET: str = Field(..., env='KITE_TOTP_SECRET')

    # SMTP
    SMTP_HOST: str = Field(..., env='SMTP_HOST')
    SMTP_PORT: int = Field(..., env='SMTP_PORT')
    SMTP_USER: str = Field(..., env='SMTP_USER')
    SMTP_PASSWORD: str = Field(..., env='SMTP_PASSWORD')

    # Logging
    LOG_LEVEL: str = Field('INFO', env='LOG_LEVEL')
    LOG_DIR: str = Field('./logs', env='LOG_DIR')


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        logger.info("Setting up configuration")
        _settings = Settings()
    return _settings

settings = get_settings()