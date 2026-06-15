# backend/app/enums/ohlcv.py

from enum import Enum as PythonEnum


class OHLCVTimeFrame(PythonEnum):
    """Enumeration for OHLCV timeframes."""
    ONE_MINUTE = "1m"
    TWO_MINUTES = "2m"
    FIVE_MINUTES = "5m"
    FIFTEEN_MINUTES = "15m"
    THIRTY_MINUTES = "30m"
    ONE_HOUR = "60m"
    ONE_DAY = "1d"


class OHLCVDataSource(PythonEnum):
    """Enumeration for OHLCV data sources."""
    YAHOO_FINANCE = "yahoo_finance"
    KITE = "kite"
