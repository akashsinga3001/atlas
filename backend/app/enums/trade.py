# backend/app/enums/trade.py

from enum import Enum as PythonEnum


class TradeStatus(PythonEnum):
    PENDING = "pending"
    OPEN = "open"
    CLOSED = "closed"


class ExitReason(PythonEnum):
    ATR_STOP = "atr_stop"
    TIMEOUT = "timeout"
    MANUAL = "manual"
