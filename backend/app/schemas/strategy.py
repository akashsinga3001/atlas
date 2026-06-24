# backend/app/schemas/strategy.py

from pydantic import BaseModel, Field
from typing import Optional


class StrategyExecutionRequest(BaseModel):
    """Schema for strategy execution request."""
    # strategy_code: Optional[str] = Field(..., description="Name of the strategy to execute.")
    strategy_version_id: Optional[int] = Field(..., description="Version ID of the strategy to execute.")
