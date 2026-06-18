# backend/app/schemas/notification.py

from pydantic import BaseModel, Field


class NotificationMetric(BaseModel):
    label: str
    value: str


class NotificationPayload(BaseModel):
    operation: str = Field(..., description="The type of operation that triggered the notification")
    status: str = Field(..., description="The status of the operation")
    duration_seconds: float = Field(..., description="The duration of the operation in seconds")
    summary: str = Field(..., description="A brief summary of the notification")
    results: list[NotificationMetric] = Field(..., description="A list of metrics related to the notification", default_factory=list)
    warnings: list[str] = Field(..., description="A list of warnings related to the notification", default_factory=list)
    action_required: list[str] = Field(..., description="A list of actions required based on the notification", default_factory=list)
