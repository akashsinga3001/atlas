# backend/app/jobs/trade_entry.py

from datetime import date

from app.celery_app import celery_app
from app.core.database import SessionLocal
from app.repositories.strategy import StrategyVersionRepository
from app.services.brokers.kite import KiteService
from app.execution_engines.registry import ExecutionEngineRegistry
from app.celery.tasks import TradeEntryTask
from app.utils.logger import get_logger

from app.schemas.strategy import TradeEntryRequest
from app.jobs.registry import register, JobDefinition

logger = get_logger(__name__)


@celery_app.task(name="app.jobs.trade_entry.run_trade_entry", bind=True, base=TradeEntryTask)
def run_trade_entry(self, strategy_id: int, allow_stale_signals: bool = False) -> dict:
    """Evaluate signals and place entry orders, dispatched to the strategy's own execution engine."""
    db = SessionLocal()
    try:
        strategy_version = StrategyVersionRepository(db).get_active_for_strategy(strategy_id)
        if not strategy_version:
            raise ValueError(f"No active StrategyVersion found for strategy {strategy_id}")

        engine_code = strategy_version.strategy.execution_engine
        engine = ExecutionEngineRegistry.get(engine_code)(db, KiteService())
        response = engine.run_entry(strategy_version=strategy_version, as_of_date=date.today(), allow_stale_signals=allow_stale_signals)

        if not response.success:
            raise RuntimeError(response.message)

        logger.info(f"Trade entry completed for strategy {strategy_id} via '{engine_code}' engine.")
        payload = response.model_dump()
        payload["engine_code"] = engine_code
        return payload
    except Exception as e:
        logger.error(f"Trade entry failed for strategy {strategy_id}: {str(e)}", exc_info=True)
        raise
    finally:
        db.close()


register(JobDefinition(name="TRADE_ENTRY", display_name="Trade Entry", description="Places entry orders for new signals — equity single-leg or options multi-leg, dispatched by the strategy's execution engine", group="trading", task=run_trade_entry, parameters_schema=TradeEntryRequest))
