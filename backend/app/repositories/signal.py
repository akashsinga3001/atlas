# backend/app/repositories/signal.py

from datetime import date
from typing import Optional
from sqlalchemy.orm import Session, joinedload

from app.models.strategy import StrategySignal, StrategyRun, StrategyVersion, Strategy
from app.repositories.base import BaseRepository


class SignalRepository(BaseRepository[StrategySignal]):

    def __init__(self, db: Session):
        super().__init__(StrategySignal, db)

    def get_signals(self, date_from: Optional[date] = None, date_to: Optional[date] = None) -> list[StrategySignal]:
        q = (self.db_session.query(StrategySignal).join(StrategyRun).options(joinedload(StrategySignal.strategy_run).joinedload(StrategyRun.strategy_version).joinedload(StrategyVersion.strategy)))
        if date_from:
            q = q.filter(StrategySignal.observed_at >= date_from)
        if date_to:
            q = q.filter(StrategySignal.observed_at <= date_to)
        return q.order_by(StrategySignal.observed_at.desc()).all()
