# backend/app/schemas/ohlcv.py

from typing import List, Optional
from pydantic import BaseModel, Field


class OHLCVImportRequest(BaseModel):
    """Schema for requesting OHLCV data import."""
    type: str = Field(..., description="The type of OHLCV data to import (e.g., 'historical', 'incremental')")
    timeframe: str = Field(None, description="The time frame for the OHLCV data (e.g., '1d', '1h')")
    securities: Optional[List[str]] = Field(None, description="Optional list of securities to import data for")
    start_date: Optional[str] = Field(None, description="The start date for the OHLCV data import (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="The end date for the OHLCV data import (YYYY-MM-DD)")
