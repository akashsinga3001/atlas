# backend/app/schemas/options.py

from datetime import date
from typing import Optional
from app.schemas.base import BaseResponse
from app.enums.options import OptionsPositionStatus, OptionsLegRole, OptionsLegStatus, OptionsExitReason


class OptionsLegResponse(BaseResponse):
    id: int
    role: OptionsLegRole
    status: OptionsLegStatus
    ticker: str
    strike: Optional[float] = None
    option_type: Optional[str] = None
    entry_fill_price: Optional[float] = None
    entry_fill_quantity: Optional[int] = None
    exit_fill_price: Optional[float] = None
    exit_fill_quantity: Optional[int] = None


class OptionsPositionResponse(BaseResponse):
    id: int
    status: OptionsPositionStatus
    signal_date: date
    entry_date: date
    spot_at_signal: float
    expiry_date: Optional[date] = None
    call_short_strike: Optional[float] = None
    put_short_strike: Optional[float] = None
    call_long_strike: Optional[float] = None
    put_long_strike: Optional[float] = None
    lots: Optional[int] = None
    lot_size: Optional[int] = None
    margin_per_lot: Optional[float] = None
    net_credit_per_lot: Optional[float] = None
    margin_total: Optional[float] = None
    net_credit_total: Optional[float] = None
    planned_exit_date: Optional[date] = None
    exit_date: Optional[date] = None
    exit_reason: Optional[OptionsExitReason] = None
    skip_reason: Optional[str] = None
    realized_pnl: Optional[float] = None
    legs: list[OptionsLegResponse] = []
