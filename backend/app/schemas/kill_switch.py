# backend/app/schemas/kill_switch.py

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from app.schemas.base import BaseResponse


class KillSwitchResponse(BaseResponse):
    enabled: bool
    reason: Optional[str] = None
    activated_at: Optional[datetime] = None
    updated_at: datetime


class ActivateKillSwitchRequest(BaseModel):
    reason: str = Field(..., min_length=1, description="Why new entries are being paused")
