"""
Application configuration settings, loaded from environment variables.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from utils.logger import logger


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', case_sensitive=False, extra='ignore')

    # Environment
    environment: str = Field('development', env='ENVIRONMENT')

    # Database
    DATABASE_URL: str = Field(..., env='DATABASE_URL')
    REDIS_URL: str = Field(..., env='REDIS_URL')
    DB_ECHO: bool = Field(False, env='DB_ECHO')

    # Celery
    CELERY_BROKER_URL: Optional[str] = Field(None, env='CELERY_BROKER_URL')
    CELERY_RESULT_BACKEND: Optional[str] = Field(None, env='CELERY_RESULT_BACKEND')
    CELERY_TIMEZONE: str = Field('Asia/Kolkata', env='CELERY_TIMEZONE')
    CELERY_ENABLE_UTC: bool = Field(False, env='CELERY_ENABLE_UTC')
    CELERY_TASK_ALWAYS_EAGER: bool = Field(False, env='CELERY_TASK_ALWAYS_EAGER')
    
    # Kite Auto-Login
    KITE_USER_ID: str = Field(..., env='KITE_USER_ID')
    KITE_PASSWORD: str = Field(..., env='KITE_PASSWORD')

    # Kite API
    KITE_API_KEY: str = Field(..., env='KITE_API_KEY')
    KITE_API_SECRET: str = Field(..., env='KITE_API_SECRET')
    KITE_TOTP_SECRET: str = Field(..., env='KITE_TOTP_SECRET')

    # SMTP
    SMTP_HOST: str = Field(..., env='SMTP_HOST')
    SMTP_PORT: int = Field(..., env='SMTP_PORT')
    SMTP_USER: str = Field(..., env='SMTP_USER')
    SMTP_PASSWORD: str = Field(..., env='SMTP_PASSWORD')

    # ML Pipeline
    ML_ARTIFACT_DIR: str = Field('./artifacts/ml', env='ML_ARTIFACT_DIR')
    ML_HORIZON_DAYS: int = Field(10, env='ML_HORIZON_DAYS')
    ML_MOVE_THRESHOLD_PCT: float = Field(5.0, env='ML_MOVE_THRESHOLD_PCT')
    ML_TOP_N_PER_DIRECTION: int = Field(5, env='ML_TOP_N_PER_DIRECTION')
    ML_MIN_TRAIN_SAMPLES: int = Field(1000, env='ML_MIN_TRAIN_SAMPLES')
    ML_REPORT_RECIPIENT: str = Field('akashsinga@gmail.com', env='ML_REPORT_RECIPIENT')
    ML_MODEL_TYPE: str = Field('ensemble', env='ML_MODEL_TYPE')  # 'rf', 'lgb', 'xgb', or 'ensemble'

    # ML Backtesting
    ML_BACKTEST_TRAIN_WINDOW_DAYS: int = Field(365, env='ML_BACKTEST_TRAIN_WINDOW_DAYS')
    ML_BACKTEST_TEST_WINDOW_DAYS: int = Field(90, env='ML_BACKTEST_TEST_WINDOW_DAYS')
    ML_BACKTEST_STEP_DAYS: int = Field(90, env='ML_BACKTEST_STEP_DAYS')
    ML_BACKTEST_PORTFOLIO_VALUE: float = Field(1_000_000.0, env='ML_BACKTEST_PORTFOLIO_VALUE')
    ML_BACKTEST_MAX_POSITION_PCT: float = Field(0.05, env='ML_BACKTEST_MAX_POSITION_PCT')
    ML_BACKTEST_MAX_OPEN_POSITIONS: int = Field(10, env='ML_BACKTEST_MAX_OPEN_POSITIONS')
    ML_BACKTEST_STOP_LOSS_PCT: float = Field(0.03, env='ML_BACKTEST_STOP_LOSS_PCT')
    ML_BACKTEST_TAKE_PROFIT_PCT: float = Field(0.08, env='ML_BACKTEST_TAKE_PROFIT_PCT')
    ML_BACKTEST_MIN_CONFIDENCE: float = Field(0.60, env='ML_BACKTEST_MIN_CONFIDENCE')
    ML_BACKTEST_COMMISSION_PCT: float = Field(0.001, env='ML_BACKTEST_COMMISSION_PCT')

    # Logging
    LOG_LEVEL: str = Field('INFO', env='LOG_LEVEL')
    LOG_DIR: str = Field('./logs', env='LOG_DIR')


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        logger.info('Setting up configuration')
        _settings = Settings()
    return _settings


settings = get_settings()