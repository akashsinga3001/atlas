# backend/app/schemas/circuit_breaker.py

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel

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
    params: Optional[dict[str, Any]] = None
