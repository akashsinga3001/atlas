# backend/jobs/ohlcv_import.py

from app.celery_app import celery_app
from app.services.ohlcv import OHLCVService
from app.utils.logger import get_logger
from app.core.database import SessionLocal
from app.celery.tasks import OHLCVImportTask

logger = get_logger(__name__)


@celery_app.task(name="app.jobs.ohlcv_import.import_ohlcv_data", bind=True, base=OHLCVImportTask)
def import_ohlcv_data(self, type: str, securities: list = None, start_date: str = None, end_date: str = None, timeframe: str = None) -> dict:
    """Import OHLCV data via scheduled Celery beat task."""
    db = SessionLocal()
    try:
        service = OHLCVService(db)
        response = service.import_ohlcv_data(type=type, securities=securities, start_date=start_date, end_date=end_date, timeframe=timeframe)

        if not response.success:
            raise RuntimeError(response.message)

        logger.info("Scheduled OHLCV data import completed.")
        return response.model_dump()
    except Exception as e:
        logger.error(f"Scheduled OHLCV data import failed: {str(e)}", exc_info=True)
        raise
    finally:
        db.close()
