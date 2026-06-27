# backend/app/services/signal.py

from datetime import date
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.ohlcv import OHLCV
from app.models.features import SecurityFeature
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

    # ── helpers ──────────────────────────────────────────────────────────────

    def _get_ohlcv_close(self, security_id: int, on_date: date) -> Optional[float]:
        row = (self.db.query(OHLCV.close).filter(OHLCV.security_id == security_id, OHLCV.timeframe == "1d", func.date(OHLCV.candle_timestamp) == on_date).first())
        return float(row[0]) if row else None

    def _get_latest_close(self, security_id: int) -> Optional[float]:
        row = (self.db.query(OHLCV.close).filter(OHLCV.security_id == security_id, OHLCV.timeframe == "1d").order_by(OHLCV.candle_timestamp.desc()).first())
        return float(row[0]) if row else None

    # ── list ─────────────────────────────────────────────────────────────────

    def get_signals(self, date_from: Optional[date] = None, date_to: Optional[date] = None, status: Optional[str] = None, strategy: Optional[str] = None) -> list[dict]:
        signals = self.signal_repo.get_signals(date_from=date_from, date_to=date_to)

        signal_ids = [s.id for s in signals]
        trades = self.db.query(Trade).filter(Trade.strategy_signal_id.in_(signal_ids)).all()
        trade_by_signal = {t.strategy_signal_id: t for t in trades}

        latest_close_cache: dict[int, Optional[float]] = {}

        result = []
        for signal in signals:
            trade = trade_by_signal.get(signal.id)
            signal_status = "entered" if trade else "missed"
            if status and status != signal_status:
                continue

            strategy_name: Optional[str] = None
            try:
                strategy_name = signal.strategy_run.strategy_version.strategy.name
            except Exception:
                pass

            if strategy and strategy_name != strategy:
                continue

            signal_close = self._get_ohlcv_close(signal.security_id, signal.observed_at.date())

            if signal.security_id not in latest_close_cache:
                latest_close_cache[signal.security_id] = self._get_latest_close(signal.security_id)
            latest_close = latest_close_cache[signal.security_id]

            perf_since_signal: Optional[float] = None
            if signal_close and latest_close:
                perf_since_signal = round((latest_close - signal_close) / signal_close * 100, 2)

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

    # ── performance detail ────────────────────────────────────────────────────

    def get_performance(self, signal_id: int) -> Optional[dict]:
        signal = self.signal_repo.get_by_id(signal_id)
        if not signal:
            return None

        trade = self.db.query(Trade).filter(Trade.strategy_signal_id == signal_id).first()

        strategy_name: Optional[str] = None
        try:
            strategy_name = signal.strategy_run.strategy_version.strategy.name
        except Exception:
            pass

        signal_date = signal.observed_at.date()

        rows = (self.db.query(OHLCV, SecurityFeature).outerjoin(SecurityFeature, SecurityFeature.ohlcv_id == OHLCV.id).filter(OHLCV.security_id == signal.security_id, OHLCV.timeframe == "1d", func.date(OHLCV.candle_timestamp) >= signal_date).order_by(OHLCV.candle_timestamp.asc()).all())

        if not rows:
            signal_close = None
            forward_data = []
        else:
            signal_close = float(rows[0][0].close)
            forward_data = self._build_forward_data(rows, signal_close, trade)

        latest_close = float(rows[-1][0].close) if rows else None
        perf_since_signal = (round((latest_close - signal_close) / signal_close * 100, 2) if signal_close and latest_close else None)

        max_close = max((r[0].close for r in rows), default=None)
        max_perf = (round((float(max_close) - signal_close) / signal_close * 100, 2) if signal_close and max_close else None)

        exit_triggered_on: Optional[str] = None
        if trade and trade.exit_date:
            exit_triggered_on = str(trade.exit_date)
        elif forward_data:
            for d in forward_data:
                if d.get("exit_triggered"):
                    exit_triggered_on = d["date"]
                    break

        fill_price = float(trade.fill_price) if trade and trade.fill_price else None
        fill_quantity = trade.fill_quantity if trade else None
        trade_pnl_pct: Optional[float] = None
        if fill_price and latest_close:
            exit_price = float(trade.exit_price) if trade and trade.exit_price else latest_close
            trade_pnl_pct = round((exit_price - fill_price) / fill_price * 100, 2)

        return {
            "signal": {
                "id": signal.id,
                "security": SecurityInfo(id=signal.security.id, ticker=signal.security.ticker, display_name=signal.security.display_name, sector=signal.security.sector, industry=signal.security.industry).model_dump(),
                "observed_at": signal.observed_at.isoformat(),
                "strategy_name": strategy_name,
                "signal_status": "entered" if trade else "missed",
                "trade_id": trade.id if trade else None,
                "trade_status": trade.status.value if trade else None,
                "fill_price": fill_price,
                "fill_quantity": fill_quantity,
                "entry_date": str(trade.entry_date) if trade else None,
                "exit_date": str(trade.exit_date) if trade and trade.exit_date else None,
                "exit_reason": trade.exit_reason.value if trade and trade.exit_reason else None,
                "timeout_date": str(trade.timeout_date) if trade else None,
            },
            "forward_data": forward_data,
            "summary": {
                "signal_close": signal_close,
                "latest_close": latest_close,
                "perf_since_signal": perf_since_signal,
                "max_close": float(max_close) if max_close else None,
                "max_perf": max_perf,
                "days_since_signal": len(rows),
                "exit_triggered_on": exit_triggered_on,
                "trade_pnl_pct": trade_pnl_pct,
                "simulated": trade is None,
            },
        }

    def _build_forward_data(self, rows: list, signal_close: float, trade: Optional[Trade]) -> list[dict]:
        if trade:
            return self._from_snapshots(rows, trade)
        return self._simulate_atr_stop(rows, signal_close)

    def _from_snapshots(self, rows: list, trade: Trade) -> list[dict]:
        snapshots_by_date = {str(s.snapshot_date): s for s in trade.snapshots}
        fill_price = float(trade.fill_price) if trade.fill_price else None

        result = []
        for ohlcv, _ in rows:
            d = str(ohlcv.candle_timestamp.date())
            snap = snapshots_by_date.get(d)
            close = float(ohlcv.close)
            mtm_pct = round((close - fill_price) / fill_price * 100, 2) if fill_price else None
            result.append({ "date": d, "close": close, "stop_price": float(snap.state.get("stop_price")) if snap and snap.state.get("stop_price") else None, "atr_14": float(snap.state.get("atr_14")) if snap and snap.state.get("atr_14") else None, "mtm_pct": float(snap.mtm_pct) if snap else mtm_pct, "exit_triggered": snap.exit_triggered if snap else False, })
        return result

    def _simulate_atr_stop(self, rows: list, signal_close: float, atr_multiplier: float = 5.0) -> list[dict]:
        highest_close = signal_close
        current_stop: Optional[float] = None
        result = []

        for ohlcv, feature in rows:
            close = float(ohlcv.close)
            atr_14 = float(feature.atr_14) if feature and feature.atr_14 else None
            mtm_pct = round((close - signal_close) / signal_close * 100, 2)

            if close > highest_close:
                highest_close = close

            stop_price: Optional[float] = None
            exit_triggered = False

            if atr_14:
                new_stop = highest_close - (atr_multiplier * atr_14)
                if current_stop is None or new_stop > current_stop:
                    current_stop = new_stop
                stop_price = round(current_stop, 2)
                exit_triggered = close <= current_stop

            result.append({ "date": str(ohlcv.candle_timestamp.date()), "close": close, "stop_price": stop_price, "atr_14": atr_14, "mtm_pct": mtm_pct, "exit_triggered": exit_triggered, })

            if exit_triggered:
                break

        return result
