# backend/app/schemas/strategy.py

from pydantic import BaseModel, Field
from typing import Optional


class StrategyExecutionRequest(BaseModel):
    """Schema for strategy execution request."""
    # strategy_code: Optional[str] = Field(..., description="Name of the strategy to execute.")
    strategy_version_id: Optional[int] = Field(..., description="Version ID of the strategy to execute.")


class TradeEntryRequest(StrategyExecutionRequest):
    """Schema for manually-triggered trade entry, with an override for stale signal runs."""
    allow_stale_signals: bool = Field(False, description="If true, allows entry on the latest strategy run even if it wasn't completed today (e.g. retrying after a failed entry attempt).")
