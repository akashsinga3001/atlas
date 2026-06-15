# backend/app/enums/job.py

from enum import Enum as PythonEnum


class JobType(PythonEnum):
    """Enum for different types of background jobs."""
    KITE_TOKEN_REFRESH = "KITE_TOKEN_REFRESH"
    SECURITIES_IMPORT = "SECURITIES_IMPORT"
    SECURITIES_ENRICHMENT = "SECURITIES_ENRICHMENT"
    OHLCV_IMPORT = "OHLCV_IMPORT"
