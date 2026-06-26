# backend/app/schemas/portfolio.py

from datetime import date
from typing import Optional
from app.schemas.base import BaseResponse


class PortfolioStats(BaseResponse):
    total_trades: int
    open_trades: int
    closed_trades: int
    win_rate: Optional[float] = None
    avg_holding_days: Optional[float] = None
    avg_win_pct: Optional[float] = None
    avg_loss_pct: Optional[float] = None
    best_trade_pct: Optional[float] = None
    worst_trade_pct: Optional[float] = None
    total_pnl: Optional[float] = None


class EquityCurvePoint(BaseResponse):
    date: date
    cumulative_pnl: float
    trade_id: int
    ticker: str
    pnl: float
