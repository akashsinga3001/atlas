# backend/app/execution_engines/options_iron_condor/engine.py

from datetime import date

from sqlalchemy.orm import Session

from app.execution_engines.base import TradeExecutionEngine
from app.models.strategy import StrategyVersion
from app.schemas.base import APIResponse
from app.services.brokers.kite import KiteService
from app.services.options_trade import OptionsTradeService


class OptionsIronCondorExecutionEngine(TradeExecutionEngine):
    """4-leg NIFTY iron condor execution, delegating to the existing OptionsTradeService unchanged."""
    code = "options_iron_condor"

    def __init__(self, db: Session, kite_service: KiteService = None):
        self._service = OptionsTradeService(db, kite_service)

    def run_entry(self, strategy_version: StrategyVersion, as_of_date: date, **kwargs) -> APIResponse:
        # allow_stale_signals has no meaning for options entry — deliberately ignored
        return self._service.run_entry(strategy_version=strategy_version, as_of_date=as_of_date)

    def run_exit_evaluation(self, strategy_version: StrategyVersion, as_of_date: date) -> APIResponse:
        return self._service.run_exit_evaluation(strategy_version=strategy_version, as_of_date=as_of_date)
