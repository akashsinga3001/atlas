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
def run_trade_exit(self, strategy_ids: list[int]) -> dict:
    """Evaluate exits for one or more strategies' open positions, each dispatched to its own execution engine."""
    if not strategy_ids:
        raise ValueError("run_trade_exit requires a non-empty strategy_ids list")

    db = SessionLocal()
    kite = KiteService()
    try:
        results = []
        for sid in strategy_ids:
            try:
                strategy_version = StrategyVersionRepository(db).get_active_for_strategy(sid)
                if not strategy_version:
                    raise ValueError(f"No active StrategyVersion found for strategy {sid}")

                engine_code = strategy_version.strategy.execution_engine
                engine = ExecutionEngineRegistry.get(engine_code)(db, kite)
                response = engine.run_exit_evaluation(strategy_version=strategy_version, as_of_date=date.today())

                if not response.success:
                    logger.error(f"Trade exit evaluation failed for strategy {sid} via '{engine_code}': {response.message}")
                results.append({"strategy_id": sid, "strategy_code": strategy_version.strategy.code, "engine_code": engine_code, "success": response.success, "message": response.message, "data": response.data})
            except Exception as e:
                logger.error(f"Trade exit evaluation raised for strategy {sid}: {e}", exc_info=True)
                db.rollback()
                results.append({"strategy_id": sid, "strategy_code": None, "engine_code": None, "success": False, "message": str(e), "data": None})

        n_ok = sum(r["success"] for r in results)
        message = f"{n_ok}/{len(results)} strategies processed successfully."
        logger.info(f"Trade exit evaluation batch complete: {message}")
        return {"success": all(r["success"] for r in results), "message": message, "data": {"results": results}}
    finally:
        db.close()


register(JobDefinition(name="TRADE_EXIT", display_name="Trade Exit", description="Evaluates exit conditions and closes/adjusts positions across one or more strategies — equity single-leg or options multi-leg, dispatched by each strategy's own execution engine", group="trading", task=run_trade_exit, parameters_schema=StrategyExecutionRequest))
