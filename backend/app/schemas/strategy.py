# backend/app/schemas/strategy.py

from datetime import datetime
from pydantic import BaseModel, Field
from typing import Any, Optional

from app.enums.strategy import StrategyRunStatus
from app.schemas.base import BaseResponse


class StrategyRunResponse(BaseResponse):
    id: int
    strategy_version_id: int
    version: int
    status: StrategyRunStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    signal_count: Optional[int] = None
    error_message: Optional[str] = None


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
    open_positions_count: int
    last_run_status: Optional[StrategyRunStatus] = None
    last_run_at: Optional[datetime] = None


class CreateStrategyVersionRequest(BaseModel):
    config: dict[str, Any] = Field(..., description="The new version's config payload")


class SetStrategyActiveRequest(BaseModel):
    is_active: bool = Field(..., description="Enable or disable the strategy — disabled strategies skip new signal generation and new entries, but existing positions continue to be managed (exits, trailing stops) unaffected")


class StrategyExecutionRequest(BaseModel):
    """Schema for strategy execution request — one or more strategies processed in a single run."""
    strategy_ids: list[int] = Field(..., min_length=1, description="IDs of the strategies whose active version(s) should run.")


class TradeEntryRequest(StrategyExecutionRequest):
    """Schema for manually-triggered trade entry, with an override for stale signal runs."""
    allow_stale_signals: bool = Field(False, description="If true, allows entry on the latest strategy run even if it wasn't completed today (e.g. retrying after a failed entry attempt).")
