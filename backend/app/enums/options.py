# backend/app/enums/options.py

from enum import Enum as PythonEnum


class OptionsPositionStatus(PythonEnum):
    PENDING = "pending"
    OPEN = "open"
    CLOSING = "closing"
    CLOSED = "closed"
    FAILED = "failed"
    SKIPPED = "skipped"


class OptionsLegRole(PythonEnum):
    SHORT_CALL = "short_call"
    SHORT_PUT = "short_put"
    LONG_CALL = "long_call"
    LONG_PUT = "long_put"


class OptionsLegStatus(PythonEnum):
    PENDING = "pending"
    OPEN = "open"
    CLOSED = "closed"
    FAILED = "failed"


class OptionsExitReason(PythonEnum):
    TIME_EXIT = "time_exit"
    EXPIRY_EXIT = "expiry_exit"
