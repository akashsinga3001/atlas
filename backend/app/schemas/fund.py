# backend/app/schemas/fund.py

from datetime import date, datetime
from typing import Optional
from pydantic import Field
from app.schemas.base import BaseResponse
from app.enums.fund import FlowType


class CashFlowCreate(BaseResponse):
    flow_type: FlowType = Field(..., description="DEPOSIT or WITHDRAWAL")
    amount: float = Field(..., gt=0, description="Amount of the cash flow, always positive")
    flow_date: date = Field(..., description="Date the cash flow occurred")
    note: Optional[str] = Field(None, max_length=255, description="Optional note about the cash flow")


class CashFlowResponse(BaseResponse):
    id: int
    flow_type: FlowType
    amount: float
    flow_date: date
    note: Optional[str] = None
    created_at: datetime


class AccountSnapshotResponse(BaseResponse):
    id: int
    snapshot_date: date
    cash_balance: float
    holdings_value: float
    total_value: float
