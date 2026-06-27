# backend/app/schemas/feature.py

from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class FeatureCalculationRequest(BaseModel):
    """Schema for requesting feature calculation."""
    type: Literal["complete", "incremental", "live_refresh"] = Field(..., description="Type of calculation to run")
    timeframe: Literal["1d", "1h", "5m"] = Field("1d", description="Candle timeframe")
    securities: Optional[List[str]] = Field(None, description="Optional list of securities to calculate features for")
    start_date: Optional[str] = Field(None, description="The start date for the feature calculation (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="The end date for the feature calculation (YYYY-MM-DD)")
