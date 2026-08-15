# backend/app/jobs/strategy_execution.py

from app.celery_app import celery_app
from app.core.database import SessionLocal
from app.repositories.strategy import StrategyRepository, StrategyVersionRepository
from app.services.strategy import StrategyService
from app.utils.logger import get_logger
from app.celery.tasks import StrategyExecutionTask

from app.schemas.strategy import StrategyExecutionRequest
from app.jobs.registry import register, JobDefinition

logger = get_logger(__name__)


@celery_app.task(name="app.jobs.strategy_execution.execute_strategy", bind=True, base=StrategyExecutionTask)
def execute_strategy(self, strategy_ids: list[int]) -> dict:
    """Execute one or more strategies' active versions, generating signals for each."""
    if not strategy_ids:
        raise ValueError("execute_strategy requires a non-empty strategy_ids list")

    db = SessionLocal()
    try:
        service = StrategyService(db)
        version_repo = StrategyVersionRepository(db)
        results = []
        for sid in strategy_ids:
            try:
                strategy_version = version_repo.get_active_for_strategy(sid)
                if not strategy_version:
                    strategy = StrategyRepository(db).get_by_id(sid)
                    logger.info(f"Skipping strategy {sid} — no active StrategyVersion (paused).")
                    results.append({"strategy_id": sid, "strategy_code": strategy.code if strategy else None, "success": True, "message": "NO_ACTIVE_VERSION", "data": None})
                    continue

                response = service.run(sid)
                if not response.success:
                    logger.error(f"Strategy execution failed for strategy {sid}: {response.message}")
                results.append({"strategy_id": sid, "strategy_code": strategy_version.strategy.code, "success": response.success, "message": response.message, "data": response.data})
            except Exception as e:
                logger.error(f"Strategy execution raised for strategy {sid}: {e}", exc_info=True)
                db.rollback()
                results.append({"strategy_id": sid, "success": False, "message": str(e), "data": None})

        n_ok = sum(r["success"] for r in results)
        message = f"{n_ok}/{len(results)} strategies executed successfully."
        logger.info(f"Strategy execution batch complete: {message}")
        return {"success": all(r["success"] for r in results), "message": message, "data": {"results": results}}
    finally:
        db.close()


register(JobDefinition(name="STRATEGY_EXECUTION", display_name="Strategy Execution", description="Runs one or more strategies' active versions and generates signals for each", group="trading", task=execute_strategy, parameters_schema=StrategyExecutionRequest))
