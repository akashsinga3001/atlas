# backend/app/utils/logger.py

import sys
from loguru import logger

from app.core.config import settings


class LoguruConfig:

    def __init__(self):
        self.log_level = settings.DEBUG and "DEBUG" or "INFO"

    @property
    def console_format(self):
        return "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"

    @classmethod
    def configure_logger(cls):
        logger.remove()
        logger.add(sink=sys.stdout, format=cls().console_format, level=cls().log_level, colorize=True, backtrace=True, diagnose=True, catch=True)


def get_logger(name: str):
    if name:
        return logger.bind(name=name)
    return logger


def log_with_context(level: str, message: str, **context):
    bound_logger = logger.bind(**context)
    getattr(bound_logger, level.lower())(message)

LoguruConfig.configure_logger()