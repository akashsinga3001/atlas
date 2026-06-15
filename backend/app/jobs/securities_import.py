# backend/app/jobs/securities_import.py

from app.celery_app import celery_app
from app.core.database import SessionLocal
from app.services.security import SecurityService
from app.utils.logger import get_logger

logger = get_logger(__name__)


@celery_app.task(name="app.jobs.securities_import.import_securities")
def import_securities() -> dict:
    """Import securities data via scheduled Celery beat task."""
    db = SessionLocal()
    try:
        service = SecurityService(db)
        response = service.import_securities()
        logger.info("Scheduled securities import completed.")
        return { "success": response.success, "message": response.message, "data": response.data }
    except Exception as e:
        logger.error(f"Scheduled securities import failed: {str(e)}", exc_info=True)
        return { "success": False, "message": "SECURITIES_IMPORT_FAILED", "data": { "error": str(e) } }
    finally:
        db.close()
