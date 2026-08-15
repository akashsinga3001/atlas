# backend/app/execution_engines/equity/engine.py

from datetime import date

from sqlalchemy.orm import Session

from app.execution_engines.base import TradeExecutionEngine
from app.models.strategy import StrategyVersion
from app.schemas.base import APIResponse
from app.services.brokers.kite import KiteService
from app.services.trade import TradeService


class EquityExecutionEngine(TradeExecutionEngine):
    """Single-leg equity execution, delegating to the existing TradeService unchanged."""
    code = "equity"

    def __init__(self, db: Session, kite_service: KiteService = None):
        self._service = TradeService(db, kite_service)

    def run_entry(self, strategy_version: StrategyVersion, as_of_date: date, **kwargs) -> APIResponse:
        return self._service.run_entry(strategy_version=strategy_version, as_of_date=as_of_date, allow_stale_signals=kwargs.get("allow_stale_signals", False))

    def run_exit_evaluation(self, strategy_version: StrategyVersion, as_of_date: date) -> APIResponse:
        return self._service.run_exit_evaluation(strategy_version=strategy_version, as_of_date=as_of_date)
