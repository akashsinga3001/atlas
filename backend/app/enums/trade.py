# backend/app/enums/trade.py

from enum import Enum as PythonEnum


class TradeStatus(PythonEnum):
    PENDING = "pending"
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class ExitReason(PythonEnum):
    ATR_STOP = "atr_stop"
    TIMEOUT = "timeout"
    MANUAL = "manual"
    RELATIVE_LEADERSHIP_DETERIORATION = "relative_leadership_deterioration"
