"""Celery task for intraday snapshot, scoring, and order routing."""

from datetime import date

from celery_app import celery_app

from services.intraday_pipeline import IntradayPipelineService
from utils.logger import logger


@celery_app.task(name='jobs.intraday.ml_intraday_execution_pipeline', bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_backoff_max=180, retry_jitter=True, retry_kwargs={'max_retries': 1})
def ml_intraday_execution_pipeline(self, run_date: str | None = None, execute_orders: bool = True) -> dict:
    """Run intraday pipeline: snapshot ingest -> inference -> external order routing."""
    logger.info('Starting intraday execution pipeline task task_id={} run_date={} execute_orders={}', self.request.id, run_date, execute_orders)
    parsed_run_date = date.fromisoformat(run_date) if run_date else None
    result = IntradayPipelineService().run(run_date=parsed_run_date, execute_orders=execute_orders)
    result['trigger_source'] = 'scheduled'
    return result
