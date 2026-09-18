# backend/app/schemas/circuit_breaker.py

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, field_validator

from app.schemas.base import BaseResponse


class CircuitBreakerResponse(BaseResponse):
    id: int
    type: str
    enabled: bool
    params: dict[str, Any]
    last_triggered_at: Optional[datetime] = None
    last_reason: Optional[str] = None
    updated_at: datetime


class UpdateCircuitBreakerRequest(BaseModel):
    enabled: Optional[bool] = None
    # params stays a generic dict — different breaker types may carry different tunable params,
    # same reasoning as MomentumScreenerConfig's extra="allow" (see CLAUDE.md's strategy-config-
    # schemas convention). threshold_pct is the one key every breaker type seeded so far actually
    # uses, so it's worth bounding specifically rather than accepting it unchecked as Any.
    params: Optional[dict[str, Any]] = None

    @field_validator("params")
    @classmethod
    def _validate_threshold_pct(cls, params: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
        if params is None or "threshold_pct" not in params:
            return params
        threshold = params["threshold_pct"]
        if not isinstance(threshold, (int, float)) or isinstance(threshold, bool) or not (0 < threshold <= 100):
            raise ValueError("threshold_pct must be a number between 0 and 100 (exclusive of 0)")
        return params
