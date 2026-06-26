# backend/app/schemas/signal.py

from datetime import datetime
from typing import Optional
from app.schemas.base import BaseResponse
from app.schemas.trade import SecurityInfo


class SignalResponse(BaseResponse):
    id: int
    security: SecurityInfo
    observed_at: datetime
    payload: dict
    strategy_run_id: int
    strategy_name: Optional[str] = None
    trade_id: Optional[int] = None
    trade_status: Optional[str] = None
    trade_fill_price: Optional[float] = None
    trade_entry_date: Optional[str] = None
    trade_pnl_pct: Optional[float] = None
    trade_pnl: Optional[float] = None
    signal_close: Optional[float] = None
    latest_close: Optional[float] = None
    perf_since_signal: Optional[float] = None
    signal_status: str
