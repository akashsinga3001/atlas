"""Celery tasks for ML training, inference, reporting, and email delivery."""

from datetime import date

from celery_app import celery_app

from services.ml_pipeline import MlPipelineService
from utils.logger import logger


@celery_app.task(name='jobs.ml.weekly_ml_train', bind=True, autoretry_for=(Exception, ), retry_backoff=True, retry_backoff_max=300, retry_jitter=True, retry_kwargs={'max_retries': 1})
def weekly_ml_train(self, run_date: str | None = None) -> dict:
    """Train long/short ML models weekly for active EQ universe."""
    logger.info('Starting weekly ML training task. task_id={} run_date={}', self.request.id, run_date)
    parsed_run_date = date.fromisoformat(run_date) if run_date else None
    service = MlPipelineService()
    result = service.run_weekly_training(run_date=parsed_run_date)
    result['trigger_source'] = 'scheduled'
    return result


@celery_app.task(name='jobs.ml.daily_ml_signal_report', bind=True, autoretry_for=(Exception, ), retry_backoff=True, retry_backoff_max=240, retry_jitter=True, retry_kwargs={'max_retries': 2})
def daily_ml_signal_report(self, send_email: bool = True) -> dict:
    """Run daily inference, create HTML report, and optionally send email."""
    logger.info('Starting daily ML signal report task. task_id={} send_email={}', self.request.id, send_email)
    service = MlPipelineService()
    result = service.run_daily_inference(send_email=send_email)
    result['trigger_source'] = 'scheduled'
    return result


@celery_app.task(name='jobs.ml.on_demand_ml_signal_report', bind=True, autoretry_for=(Exception, ), retry_backoff=True, retry_backoff_max=240, retry_jitter=True, retry_kwargs={'max_retries': 2})
def on_demand_ml_signal_report(self, reason: str = 'manual_run', send_email: bool = True) -> dict:
    """Run on-demand inference/report pipeline for manual execution."""
    logger.info('Starting on-demand ML signal report task. task_id={} reason={} send_email={}', self.request.id, reason, send_email)
    service = MlPipelineService()
    result = service.run_daily_inference(send_email=send_email)
    result['trigger_source'] = 'on_demand'
    result['reason'] = reason
    return result
