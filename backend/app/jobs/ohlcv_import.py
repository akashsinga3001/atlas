# backend/jobs/ohlcv_import.py

from app.celery_app import celery_app
from app.services.ohlcv import OHLCVService
from app.utils.logger import get_logger
from app.core.database import SessionLocal

logger = get_logger(__name__)


@celery_app.task(name="app.jobs.ohlcv_import.import_ohlcv_data")
def import_ohlcv_data(type: str, securities: list = None, start_date: str = None, end_date: str = None, timeframe: str = None) -> dict:
    """Import OHLCV data via scheduled Celery beat task."""
    db = SessionLocal()
    try:
        service = OHLCVService(db)
        response = service.import_ohlcv_data(type=type, securities=securities, start_date=start_date, end_date=end_date, timeframe=timeframe)
        logger.info("Scheduled OHLCV data import completed.")
        return { "success": response.success, "message": response.message, "data": response.data }
    except Exception as e:
        logger.error(f"Scheduled OHLCV data import failed: {str(e)}", exc_info=True)
        return { "success": False, "message": "OHLCV_IMPORT_FAILED", "data": { "error": str(e) } }
    finally:
        db.close()
