# backend/app/enums/security.py

from enum import Enum as PythonEnum


class SecurityType(PythonEnum):
    """Enum for security types."""
    EQUITY = "EQUITY"
    INDEX = "INDEX"
    FUT = "FUT"
    OPTION = "OPTION"


class SecurityExchange(PythonEnum):
    """Enum for security exchanges."""
    NSE = "NSE"
    BSE = "BSE"
    NFO_FUT = "NFO-FUT"
    NFO_OPT = "NFO-OPT"
    BSE_FUT = "BSE-FUT"
    BSE_OPT = "BSE-OPT"
