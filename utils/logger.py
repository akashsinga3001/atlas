"""Shared project logger configuration.

Provides a single configured loguru logger instance used across the project.
"""

from os import getenv, makedirs
from os.path import join

from loguru import logger as _logger


_IS_CONFIGURED = False


def _normalize_level(level: str | None) -> str:
    """Normalize configured log level with a safe fallback."""
    if not level:
        return 'INFO'

    normalized = level.strip().upper()
    valid_levels = {
        'TRACE',
        'DEBUG',
        'INFO',
        'SUCCESS',
        'WARNING',
        'ERROR',
        'CRITICAL',
    }
    return normalized if normalized in valid_levels else 'INFO'


def _configure_logger() -> None:
    """Configure terminal and file sinks once for the shared logger."""
    global _IS_CONFIGURED
    if _IS_CONFIGURED:
        return

    log_level = _normalize_level(getenv('LOG_LEVEL', 'INFO'))
    log_dir = getenv('LOG_DIR', './logs')
    makedirs(log_dir, exist_ok=True)

    format_template = (
        '<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> '
        '| <level>{level: <8}</level> '
        '| <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> '
        '| pid=<magenta>{process.id}</magenta> '
        '| <level>{message}</level>'
    )

    _logger.remove()
    _logger.add(
        sink=lambda message: print(message, end=''),
        level=log_level,
        format=format_template,
        colorize=True,
        enqueue=True,
    )
    _logger.add(
        sink=join(log_dir, '{time:YYYY-MM-DD}.log'),
        rotation='00:00',
        level=log_level,
        format=format_template,
        colorize=False,
        enqueue=True,
    )

    _IS_CONFIGURED = True


_configure_logger()
logger = _logger
