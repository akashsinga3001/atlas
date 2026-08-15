# backend/app/schemas/strategy.py

from datetime import datetime
from pydantic import BaseModel, Field
from typing import Any, Optional

from app.schemas.base import BaseResponse


class StrategyVersionResponse(BaseResponse):
    id: int
    strategy_id: int
    version: int
    config: dict[str, Any]
    implementation_class: str
    exit_evaluator_class: Optional[str] = None
    is_active: bool
    created_at: datetime


class StrategyResponse(BaseResponse):
    id: int
    code: str
    name: str
    is_active: bool
    has_config_schema: bool
    config_fields: list[dict]
    active_version: Optional[StrategyVersionResponse] = None
    version_count: int


class CreateStrategyVersionRequest(BaseModel):
    config: dict[str, Any] = Field(..., description="The new version's config payload")


class StrategyExecutionRequest(BaseModel):
    """Schema for strategy execution request."""
    # strategy_code: Optional[str] = Field(..., description="Name of the strategy to execute.")
    strategy_version_id: Optional[int] = Field(..., description="Version ID of the strategy to execute.")


class TradeEntryRequest(StrategyExecutionRequest):
    """Schema for manually-triggered trade entry, with an override for stale signal runs."""
    allow_stale_signals: bool = Field(False, description="If true, allows entry on the latest strategy run even if it wasn't completed today (e.g. retrying after a failed entry attempt).")
