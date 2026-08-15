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
def run_trade_entry(self, strategy_ids: list[int] | None = None, strategy_id: int | None = None, allow_stale_signals: bool = False) -> dict:
    """Evaluate signals and place entry orders for one or more strategies, each dispatched to its own execution engine."""
    if strategy_ids is None:
        if strategy_id is None:
            raise ValueError("run_trade_entry requires a non-empty strategy_ids list")
        logger.warning(f"run_trade_entry invoked with legacy singular strategy_id={strategy_id} — the schedule_entries.kwargs migration/resync has not run for this row yet.")
        strategy_ids = [strategy_id]
    if not strategy_ids:
        raise ValueError("run_trade_entry requires a non-empty strategy_ids list")

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
                response = engine.run_entry(strategy_version=strategy_version, as_of_date=date.today(), allow_stale_signals=allow_stale_signals)

                if not response.success:
                    logger.error(f"Trade entry failed for strategy {sid} via '{engine_code}': {response.message}")
                results.append({"strategy_id": sid, "strategy_code": strategy_version.strategy.code, "engine_code": engine_code, "success": response.success, "message": response.message, "data": response.data})
            except Exception as e:
                logger.error(f"Trade entry raised for strategy {sid}: {e}", exc_info=True)
                db.rollback()
                results.append({"strategy_id": sid, "strategy_code": None, "engine_code": None, "success": False, "message": str(e), "data": None})

        n_ok = sum(r["success"] for r in results)
        message = f"{n_ok}/{len(results)} strategies processed successfully."
        logger.info(f"Trade entry batch complete: {message}")
        return {"success": all(r["success"] for r in results), "message": message, "data": {"results": results}}
    finally:
        db.close()


register(JobDefinition(name="TRADE_ENTRY", display_name="Trade Entry", description="Places entry orders for new signals across one or more strategies — equity single-leg or options multi-leg, dispatched by each strategy's own execution engine", group="trading", task=run_trade_entry, parameters_schema=TradeEntryRequest))
