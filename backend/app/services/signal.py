# backend/app/services/signal.py

from datetime import date
from typing import Optional
from sqlalchemy.orm import Session

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

    def get_signals(self, date_from: Optional[date] = None, date_to: Optional[date] = None, status: Optional[str] = None) -> list[dict]:
        signals = self.signal_repo.get_signals(date_from=date_from, date_to=date_to)

        signal_ids = [s.id for s in signals]
        trades = self.db.query(Trade).filter(Trade.strategy_signal_id.in_(signal_ids)).all()
        trade_by_signal = {t.strategy_signal_id: t for t in trades}

        result = []
        for signal in signals:
            trade = trade_by_signal.get(signal.id)
            signal_status = "entered" if trade else "missed"
            if status and status != signal_status:
                continue
            result.append(
                SignalResponse(
                    id=signal.id, security=SecurityInfo(id=signal.security.id, ticker=signal.security.ticker, display_name=signal.security.display_name, sector=signal.security.sector, industry=signal.security.industry), observed_at=signal.observed_at, payload=signal.payload or {}, strategy_run_id=signal.strategy_run_id, trade_id=trade.id if trade else None, trade_status=trade.status.value if trade else None, trade_fill_price=float(trade.fill_price) if trade and trade.fill_price else None,
                    trade_entry_date=str(trade.entry_date) if trade else None, signal_status=signal_status
                ).model_dump()
            )

        return result
