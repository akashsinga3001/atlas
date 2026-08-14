# backend/app/jobs/iron_condor_exit.py

from datetime import date

from app.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.strategy import StrategyVersion
from app.services.brokers.kite import KiteService
from app.services.options_trade import OptionsTradeService
from app.celery.tasks import IronCondorExitTask
from app.utils.logger import get_logger

from app.schemas.strategy import StrategyExecutionRequest
from app.jobs.registry import register, JobDefinition

logger = get_logger(__name__)


@celery_app.task(name="app.jobs.iron_condor_exit.run_iron_condor_exit", bind=True, base=IronCondorExitTask)
def run_iron_condor_exit(self, strategy_version_id: int) -> dict:
    """Close any iron condor position past its planned exit date, and unwind failed-entry leftovers."""
    db = SessionLocal()
    try:
        strategy_version = db.query(StrategyVersion).filter(StrategyVersion.id == strategy_version_id).first()
        if not strategy_version:
            raise ValueError(f"StrategyVersion {strategy_version_id} not found")

        kite_service = KiteService()
        service = OptionsTradeService(db, kite_service)
        response = service.run_exit_evaluation(strategy_version=strategy_version, as_of_date=date.today())

        if not response.success:
            raise RuntimeError(response.message)

        logger.info(f"Iron condor exit evaluation completed for strategy version {strategy_version_id}.")
        return response.model_dump()
    except Exception as e:
        logger.error(f"Iron condor exit evaluation failed for version {strategy_version_id}: {str(e)}", exc_info=True)
        raise
    finally:
        db.close()


register(JobDefinition(name="IRON_CONDOR_EXIT", display_name="Iron Condor Exit", description="Evaluates and executes iron condor position exits", group="trading", task=run_iron_condor_exit, parameters_schema=StrategyExecutionRequest))
