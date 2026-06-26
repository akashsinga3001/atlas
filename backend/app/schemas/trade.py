# backend/app/schemas/trade.py

from datetime import date
from typing import Optional
from app.schemas.base import BaseResponse
from app.enums.trade import TradeStatus, ExitReason


class SecurityInfo(BaseResponse):
    id: int
    ticker: str
    display_name: str
    sector: Optional[str] = None
    industry: Optional[str] = None


class TradeResponse(BaseResponse):
    id: int
    security: SecurityInfo
    status: TradeStatus
    entry_date: date
    fill_price: Optional[float] = None
    fill_quantity: Optional[int] = None
    timeout_date: date
    exit_date: Optional[date] = None
    exit_reason: Optional[ExitReason] = None
    state: dict
    invested_value: Optional[float] = None
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
