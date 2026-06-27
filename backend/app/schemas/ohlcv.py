# backend/app/schemas/ohlcv.py

from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class OHLCVImportRequest(BaseModel):
    """Schema for requesting OHLCV data import."""
    type: Literal["historical", "incremental", "live_refresh"] = Field(..., description="Type of import to run")
    timeframe: Literal["1d", "1h", "5m"] = Field("1d", description="Candle timeframe")
    securities: Optional[List[str]] = Field(None, description="Optional list of securities to import data for")
    start_date: Optional[str] = Field(None, description="The start date for the OHLCV data import (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="The end date for the OHLCV data import (YYYY-MM-DD)")
