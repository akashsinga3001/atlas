# backend/app/enums/trade.py

from enum import Enum as PythonEnum


class TradeStatus(PythonEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class ExitReason(PythonEnum):
    ATR_STOP = "atr_stop"
    TIMEOUT = "timeout"
    MANUAL = "manual"
