# backend/app/enums/security.py

from enum import Enum as PythonEnum


class SecurityType(PythonEnum):
    """Enum for security types."""
    EQUITY = "EQUITY"
    INDEX = "INDEX"


class SecurityExchange(PythonEnum):
    """Enum for security exchanges."""
    NSE = "NSE"
    BSE = "BSE"
