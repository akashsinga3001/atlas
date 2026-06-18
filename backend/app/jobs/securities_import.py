# backend/app/jobs/securities_import.py

from app.celery_app import celery_app
from app.core.database import SessionLocal
from app.services.security import SecurityService
from app.utils.logger import get_logger
from app.celery.tasks import SecuritiesImportTask

logger = get_logger(__name__)


@celery_app.task(name="app.jobs.securities_import.import_securities", bind=True, base=SecuritiesImportTask)
def import_securities(self) -> dict:
    """Import securities data via scheduled Celery beat task."""
    db = SessionLocal()
    try:
        service = SecurityService(db)
        response = service.import_securities()

        if not response.success:
            raise RuntimeError(response.message)

        logger.info("Scheduled securities import completed.")
        return response.model_dump()
    except Exception as e:
        logger.error(f"Scheduled securities import failed: {str(e)}", exc_info=True)
        raise
    finally:
        db.close()
