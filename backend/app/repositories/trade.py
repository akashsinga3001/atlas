# backend/app/repositories/trade.py

from datetime import date
from typing import Optional
from sqlalchemy.orm import Session

from app.enums.trade import TradeStatus
from app.models.trade import Trade, TradeSnapshot
from app.repositories.base import BaseRepository


class TradeRepository(BaseRepository[Trade]):
    """Repository class for managing Trade data in the database."""

    def __init__(self, db: Session):
        self.db = db
        super().__init__(Trade, db)

    def get_open_trades(self) -> list[Trade]:
        """Fetch all trades that are currently open (status is OPEN)."""
        return self.db.query(Trade).filter(Trade.status == TradeStatus.OPEN).all()

    def get_pending_trades(self) -> list[Trade]:
        """Fetch all trades that are currently pending (status is PENDING)."""
        return self.db.query(Trade).filter(Trade.status == TradeStatus.PENDING).all()

    def get_open_trades_for_strategy_version(self, strategy_version_id: int) -> list[Trade]:
        """Fetch all active (OPEN or PENDING) trades for a specific strategy version."""
        return self.db.query(Trade).filter(Trade.strategy_version_id == strategy_version_id, Trade.status.in_([TradeStatus.OPEN, TradeStatus.PENDING])).all()

    def get_by_security_and_status(self, security_id: int, status: TradeStatus) -> Optional[Trade]:
        """Fetch a trade by security ID and status."""
        return self.db.query(Trade).filter(Trade.security_id == security_id, Trade.status == status).first()

    def get_timed_out_trades(self, as_of_date: date) -> list[Trade]:
        """Fetch all trades that have timed out as of a specific date."""
        return self.db.query(Trade).filter(Trade.timeout_date <= as_of_date, Trade.status == TradeStatus.OPEN).all()

    def get_all_trades(self, status: Optional[TradeStatus] = None) -> list[Trade]:
        """Fetch all trades, optionally filtered by status."""
        query = self.db.query(Trade)
        if status:
            query = query.filter(Trade.status == status)
        return query.order_by(Trade.entry_date.desc()).all()

    def get_closed_trades_ordered(self) -> list[Trade]:
        """Fetch all closed trades ordered by exit date."""
        return self.db.query(Trade).filter(Trade.status == TradeStatus.CLOSED, Trade.exit_price.isnot(None)).order_by(Trade.exit_date).all()


class TradeSnapshotRepository(BaseRepository[TradeSnapshot]):
    """Repository class for managing TradeSnapshot data in the database."""

    def __init__(self, db: Session):
        self.db = db
        super().__init__(TradeSnapshot, db)

    def get_for_trade_on_date(self, trade_id: int, snapshot_date: date) -> Optional[TradeSnapshot]:
        """Fetch a trade snapshot for a specific trade on a given date."""
        return self.db.query(TradeSnapshot).filter(TradeSnapshot.trade_id == trade_id, TradeSnapshot.snapshot_date == snapshot_date).first()
