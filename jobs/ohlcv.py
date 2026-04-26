"""Celery tasks for OHLCV ingestion and aggregation."""

from celery import shared_task

from services.ohlcv import OhlcvService
from utils.logger import logger


@shared_task(name='jobs.ohlcv.daily_ohlcv_upsert', bind=True, autoretry_for=(Exception, ), retry_backoff=True, retry_backoff_max=180, retry_jitter=True, retry_kwargs={'max_retries': 2})
def daily_ohlcv_upsert(self, force_backfill: bool = False) -> dict:
    """Run daily 1DAY OHLCV upsert for active EQ and NFO FUT instruments."""
    logger.info('Starting daily OHLCV upsert task. force_backfill={}', force_backfill)
    service = OhlcvService()
    result = service.upsert_daily_ohlcv(force_backfill=force_backfill)
    result['trigger_source'] = 'scheduled'
    return result


@shared_task(name='jobs.ohlcv.daily_ohlcv_pipeline', bind=True, autoretry_for=(Exception, ), retry_backoff=True, retry_backoff_max=240, retry_jitter=True, retry_kwargs={'max_retries': 2})
def daily_ohlcv_pipeline(self, force_backfill: bool = False, feature_lookback_days: int = 90) -> dict:
    """Run post-close OHLCV ingestion, aggregation, and feature upsert in strict sequence."""
    logger.info('Starting daily OHLCV pipeline task. force_backfill={} feature_lookback_days={}', force_backfill, feature_lookback_days)
    service = OhlcvService()
    result = service.run_daily_pipeline(force_backfill=force_backfill, feature_lookback_days=feature_lookback_days)
    result['trigger_source'] = 'scheduled'
    return result


@shared_task(name='jobs.ohlcv.on_demand_ohlcv_upsert', bind=True, autoretry_for=(Exception, ), retry_backoff=True, retry_backoff_max=180, retry_jitter=True, retry_kwargs={'max_retries': 2})
def on_demand_ohlcv_upsert(self, reason: str = 'manual_run', force_backfill: bool = False) -> dict:
    """Run on-demand 1DAY OHLCV upsert for active EQ and NFO FUT instruments."""
    logger.info('Starting on-demand OHLCV upsert task. reason={} force_backfill={}', reason, force_backfill)
    service = OhlcvService()
    result = service.upsert_daily_ohlcv(force_backfill=force_backfill)
    result['trigger_source'] = 'on_demand'
    result['reason'] = reason
    return result


@shared_task(name='jobs.ohlcv.daily_ohlcv_aggregate_week', bind=True, autoretry_for=(Exception, ), retry_backoff=True, retry_backoff_max=180, retry_jitter=True, retry_kwargs={'max_retries': 2})
def daily_ohlcv_aggregate_week(self) -> dict:
    """Aggregate 1DAY OHLCV into 1WEEK OHLCV."""
    logger.info('Starting daily OHLCV weekly aggregation task')
    service = OhlcvService()
    result = service.aggregate_from_daily(target_timeframe='1WEEK')
    result['trigger_source'] = 'scheduled'
    return result


@shared_task(name='jobs.ohlcv.daily_ohlcv_aggregate_month', bind=True, autoretry_for=(Exception, ), retry_backoff=True, retry_backoff_max=180, retry_jitter=True, retry_kwargs={'max_retries': 2})
def daily_ohlcv_aggregate_month(self) -> dict:
    """Aggregate 1DAY OHLCV into 1MONTH OHLCV."""
    logger.info('Starting daily OHLCV monthly aggregation task')
    service = OhlcvService()
    result = service.aggregate_from_daily(target_timeframe='1MONTH')
    result['trigger_source'] = 'scheduled'
    return result
