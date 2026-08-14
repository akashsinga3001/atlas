# backend/app/jobs/iron_condor_option_chain_import.py

from app.celery_app import celery_app
from app.core.database import SessionLocal
from app.services.options_chain import OptionsChainService
from app.celery.tasks import IronCondorOptionChainImportTask
from app.utils.logger import get_logger

from app.jobs.registry import register, JobDefinition

logger = get_logger(__name__)


@celery_app.task(name="app.jobs.iron_condor_option_chain_import.import_iron_condor_option_chain", bind=True, base=IronCondorOptionChainImportTask)
def import_iron_condor_option_chain(self, name: str = "NIFTY") -> dict:
    """Refresh the NFO option-contract universe (weekly + monthly) for the given underlying."""
    db = SessionLocal()
    try:
        service = OptionsChainService(db)
        response = service.import_nifty_option_chain(name=name)

        if not response.success:
            raise RuntimeError(response.message)

        logger.info(f"Iron condor option chain import completed for {name}.")
        return response.model_dump()
    except Exception as e:
        logger.error(f"Iron condor option chain import failed for {name}: {str(e)}", exc_info=True)
        raise
    finally:
        db.close()


register(JobDefinition(name="IRON_CONDOR_OPTION_CHAIN_IMPORT", display_name="Iron Condor Option Chain Import", description="Refreshes the NIFTY weekly option-contract universe", group="trading", task=import_iron_condor_option_chain))
