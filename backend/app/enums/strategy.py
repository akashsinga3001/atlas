# backend/app/enums/strategy.py

from enum import Enum as PythonEnum


class StrategyRunStatus(PythonEnum):
    """Enum for different statuses of a strategy run."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
