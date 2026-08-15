# backend/app/jobs/trade_exit.py

from datetime import date

from app.celery_app import celery_app
from app.core.database import SessionLocal
from app.repositories.strategy import StrategyVersionRepository
from app.services.brokers.kite import KiteService
from app.execution_engines.registry import ExecutionEngineRegistry
from app.celery.tasks import TradeExitTask
from app.utils.logger import get_logger

from app.schemas.strategy import StrategyExecutionRequest
from app.jobs.registry import register, JobDefinition

logger = get_logger(__name__)


@celery_app.task(name="app.jobs.trade_exit.run_trade_exit", bind=True, base=TradeExitTask)
def run_trade_exit(self, strategy_id: int) -> dict:
    """Evaluate exits for all open positions under a strategy's active version, dispatched to its execution engine."""
    db = SessionLocal()
    try:
        strategy_version = StrategyVersionRepository(db).get_active_for_strategy(strategy_id)
        if not strategy_version:
            raise ValueError(f"No active StrategyVersion found for strategy {strategy_id}")

        engine_code = strategy_version.strategy.execution_engine
        engine = ExecutionEngineRegistry.get(engine_code)(db, KiteService())
        response = engine.run_exit_evaluation(strategy_version=strategy_version, as_of_date=date.today())

        if not response.success:
            raise RuntimeError(response.message)

        logger.info(f"Trade exit evaluation completed for strategy {strategy_id} via '{engine_code}' engine.")
        payload = response.model_dump()
        payload["engine_code"] = engine_code
        return payload
    except Exception as e:
        logger.error(f"Trade exit evaluation failed for strategy {strategy_id}: {str(e)}", exc_info=True)
        raise
    finally:
        db.close()


register(JobDefinition(name="TRADE_EXIT", display_name="Trade Exit", description="Evaluates exit conditions and closes/adjusts positions — equity single-leg or options multi-leg, dispatched by the strategy's execution engine", group="trading", task=run_trade_exit, parameters_schema=StrategyExecutionRequest))
