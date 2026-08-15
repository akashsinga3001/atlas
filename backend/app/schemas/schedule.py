# backend/app/schemas/schedule.py

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field

from app.schemas.base import BaseResponse


class ScheduleEntryResponse(BaseResponse):
    id: int
    name: str
    task: str
    minute: str
    hour: str
    day_of_week: str
    day_of_month: str
    month_of_year: str
    kwargs: dict[str, Any]
    enabled: bool
    description: Optional[str] = None
    group: str
    created_at: datetime
    updated_at: datetime


class CreateScheduleEntryRequest(BaseModel):
    name: str = Field(..., description="Unique name for this schedule entry")
    task: str = Field(..., description="Dotted Celery task path, e.g. app.jobs.trade_entry.run_trade_entry")
    minute: str = Field("*", description="Cron minute field")
    hour: str = Field("*", description="Cron hour field")
    day_of_week: str = Field("*", description="Cron day-of-week field")
    day_of_month: str = Field("*", description="Cron day-of-month field")
    month_of_year: str = Field("*", description="Cron month-of-year field")
    kwargs: dict[str, Any] = Field(default_factory=dict, description="Keyword arguments passed to the task")
    enabled: bool = Field(True, description="Whether this entry is currently active")
    description: Optional[str] = Field(None, description="Human-readable description")
    group: str = Field("trading", description="UI grouping — data_pipeline or trading")


class UpdateScheduleEntryRequest(BaseModel):
    task: Optional[str] = None
    minute: Optional[str] = None
    hour: Optional[str] = None
    day_of_week: Optional[str] = None
    day_of_month: Optional[str] = None
    month_of_year: Optional[str] = None
    kwargs: Optional[dict[str, Any]] = None
    description: Optional[str] = None
    group: Optional[str] = None


class ToggleScheduleEntryRequest(BaseModel):
    enabled: bool = Field(..., description="New enabled state")
