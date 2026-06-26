# backend/app/services/signal.py

from datetime import date
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.ohlcv import OHLCV
from app.models.trade import Trade
from app.repositories.signal import SignalRepository
from app.schemas.signal import SignalResponse
from app.schemas.trade import SecurityInfo
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SignalService:

    def __init__(self, db: Session):
        self.db = db
        self.signal_repo = SignalRepository(db)

    def _get_ohlcv_close(self, security_id: int, on_date: date) -> Optional[float]:
        row = (self.db.query(OHLCV.close).filter(OHLCV.security_id == security_id, OHLCV.timeframe == "1d", func.date(OHLCV.candle_timestamp) == on_date).first())
        return float(row[0]) if row else None

    def _get_latest_close(self, security_id: int) -> Optional[float]:
        row = (self.db.query(OHLCV.close).filter(OHLCV.security_id == security_id, OHLCV.timeframe == "1d").order_by(OHLCV.candle_timestamp.desc()).first())
        return float(row[0]) if row else None

    def get_signals(self, date_from: Optional[date] = None, date_to: Optional[date] = None, status: Optional[str] = None) -> list[dict]:
        signals = self.signal_repo.get_signals(date_from=date_from, date_to=date_to)

        signal_ids = [s.id for s in signals]
        trades = self.db.query(Trade).filter(Trade.strategy_signal_id.in_(signal_ids)).all()
        trade_by_signal = {t.strategy_signal_id: t for t in trades}

        # Cache latest closes per security to avoid repeated queries
        latest_close_cache: dict[int, Optional[float]] = {}

        result = []
        for signal in signals:
            trade = trade_by_signal.get(signal.id)
            signal_status = "entered" if trade else "missed"
            if status and status != signal_status:
                continue

            # Strategy name via eager-loaded relations
            strategy_name: Optional[str] = None
            try:
                strategy_name = signal.strategy_run.strategy_version.strategy.name
            except Exception:
                pass

            # OHLCV prices for perf_since_signal
            signal_close = self._get_ohlcv_close(signal.security_id, signal.observed_at.date())

            if signal.security_id not in latest_close_cache:
                latest_close_cache[signal.security_id] = self._get_latest_close(signal.security_id)
            latest_close = latest_close_cache[signal.security_id]

            perf_since_signal: Optional[float] = None
            if signal_close and latest_close:
                perf_since_signal = round((latest_close - signal_close) / signal_close * 100, 2)

            # Trade P&L
            trade_pnl_pct: Optional[float] = None
            trade_pnl: Optional[float] = None
            fill_price = float(trade.fill_price) if trade and trade.fill_price else None
            fill_quantity = trade.fill_quantity if trade else None

            if fill_price:
                exit_price = float(trade.exit_price) if trade and trade.exit_price else None
                reference_price = exit_price or latest_close
                if reference_price:
                    trade_pnl_pct = round((reference_price - fill_price) / fill_price * 100, 2)
                    if fill_quantity:
                        trade_pnl = round((reference_price - fill_price) * fill_quantity, 2)

            result.append(
                SignalResponse(
                    id=signal.id, security=SecurityInfo(id=signal.security.id, ticker=signal.security.ticker, display_name=signal.security.display_name, sector=signal.security.sector, industry=signal.security.industry), observed_at=signal.observed_at, payload=signal.payload or {}, strategy_run_id=signal.strategy_run_id, strategy_name=strategy_name, trade_id=trade.id if trade else None, trade_status=trade.status.value if trade else None, trade_fill_price=fill_price,
                    trade_entry_date=str(trade.entry_date) if trade else None, trade_pnl_pct=trade_pnl_pct, trade_pnl=trade_pnl, signal_close=signal_close, latest_close=latest_close, perf_since_signal=perf_since_signal, signal_status=signal_status,
                ).model_dump()
            )

        return result
