# backend/app/schemas/feature.py

from typing import List, Optional
from pydantic import BaseModel, Field


class FeatureCalculationRequest(BaseModel):
    """Schema for requesting feature calculation."""
    type: str = Field(..., description="The type of feature calculation to perform (e.g., 'complete', 'incremental')")
    timeframe: str = Field(None, description="The time frame for the feature calculation (e.g., '1d', '1h')")
    securities: Optional[List[str]] = Field(None, description="Optional list of securities to calculate features for")
    start_date: Optional[str] = Field(None, description="The start date for the feature calculation (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="The end date for the feature calculation (YYYY-MM-DD)")
