# backend/app/jobs/strategy_execution.py

from app.celery_app import celery_app
from app.core.database import SessionLocal
from app.services.strategy import StrategyService
from app.utils.logger import get_logger
from app.celery.tasks import StrategyExecutionTask

logger = get_logger(__name__)


@celery_app.task(name="app.jobs.strategy_execution.execute_strategy", bind=True, base=StrategyExecutionTask)
def execute_strategy(self, strategy_version_id: int) -> dict:
    """Execute a strategy via Celery task."""
    db = SessionLocal()
    try:
        service = StrategyService(db)
        response = service.run(strategy_version_id)

        if not response.success:
            raise RuntimeError(response.message)

        logger.info(f"Strategy execution completed for version {strategy_version_id}.")
        return response.model_dump()
    except Exception as e:
        logger.error(f"Strategy execution failed for version {strategy_version_id}: {str(e)}", exc_info=True)
        raise
    finally:
        db.close()
