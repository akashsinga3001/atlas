"""Celery tasks for OHLCV feature computation."""

from celery_app import celery_app

from services.feature import FeatureService
from utils.logger import logger


@celery_app.task(name='jobs.features.daily_features_upsert', bind=True, autoretry_for=(Exception, ), retry_backoff=True, retry_backoff_max=180, retry_jitter=True, retry_kwargs={'max_retries': 2})
def daily_features_upsert(self, lookback_days: int = 90) -> dict:
    """Compute and upsert OHLCV features for 1DAY, 1WEEK, 1MONTH candles."""
    logger.info('Starting daily features upsert task. lookback_days={}', lookback_days)
    service = FeatureService()
    result = service.upsert_features(lookback_days=lookback_days)
    result['trigger_source'] = 'scheduled'
    return result


@celery_app.task(name='jobs.features.on_demand_features_upsert', bind=True, autoretry_for=(Exception, ), retry_backoff=True, retry_backoff_max=180, retry_jitter=True, retry_kwargs={'max_retries': 2})
def on_demand_features_upsert(self, reason: str = 'manual_run', lookback_days: int = 90) -> dict:
    """Compute and upsert OHLCV features for manual execution."""
    logger.info('Starting on-demand features upsert task. reason={} lookback_days={}', reason, lookback_days)
    service = FeatureService()
    result = service.upsert_features(lookback_days=lookback_days)
    result['trigger_source'] = 'on_demand'
    result['reason'] = reason
    return result
