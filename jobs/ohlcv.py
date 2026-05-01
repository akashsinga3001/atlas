"""Celery tasks for OHLCV ingestion and aggregation."""

from celery_app import celery_app

from services.ohlcv import OhlcvService
from utils.logger import logger


@celery_app.task(name='jobs.ohlcv.daily_ohlcv_upsert', bind=True, autoretry_for=(Exception, ), retry_backoff=True, retry_backoff_max=180, retry_jitter=True, retry_kwargs={'max_retries': 2})
def daily_ohlcv_upsert(self, force_backfill: bool = False) -> dict:
    """Run daily 1DAY OHLCV upsert for active EQ and NFO FUT instruments."""
    logger.info('Starting daily OHLCV upsert task. task_id={} force_backfill={}', self.request.id, force_backfill)
    service = OhlcvService()
    result = service.upsert_daily_ohlcv(force_backfill=force_backfill)
    logger.info(
        'Completed daily OHLCV upsert task. task_id={} success={} processed={} inserted_or_updated={} errors={}',
        self.request.id,
        result.get('success', False),
        result.get('processed', 0),
        result.get('inserted_or_updated', 0),
        result.get('errors_count', 0),
    )
    result['trigger_source'] = 'scheduled'
    return result


@celery_app.task(name='jobs.ohlcv.daily_ohlcv_pipeline', bind=True, autoretry_for=(Exception, ), retry_backoff=True, retry_backoff_max=240, retry_jitter=True, retry_kwargs={'max_retries': 2})
def daily_ohlcv_pipeline(self, force_backfill: bool = False, feature_lookback_days: int = 90, feature_backfill: bool = False) -> dict:
    """Run post-close OHLCV ingestion, aggregation, and feature upsert in strict sequence.
    
    Args:
        force_backfill: Force 5-year backfill for OHLCV ingestion
        feature_lookback_days: Days to lookback for feature calculation (ignored if feature_backfill=True)
        feature_backfill: If True, calculate features for ALL OHLCV records (one-time backfill)
    """
    logger.info(
        'Starting daily OHLCV pipeline task. task_id={} force_backfill={} feature_lookback_days={} feature_backfill={}',
        self.request.id,
        force_backfill,
        feature_lookback_days,
        feature_backfill,
    )
    service = OhlcvService()
    result = service.run_daily_pipeline(force_backfill=force_backfill, feature_lookback_days=feature_lookback_days, feature_backfill=feature_backfill)
    logger.info(
        'Completed daily OHLCV pipeline task. task_id={} success={} ingestion_processed={} ingestion_errors={} weekly_groups={} monthly_groups={} features_processed={}',
        self.request.id,
        result.get('success', False),
        result.get('ingestion', {}).get('processed', 0),
        result.get('ingestion', {}).get('errors_count', 0),
        result.get('weekly_aggregation', {}).get('groups_aggregated', 0),
        result.get('monthly_aggregation', {}).get('groups_aggregated', 0),
        result.get('features', {}).get('candles_processed', 0),
    )
    result['trigger_source'] = 'scheduled'
    return result


@celery_app.task(name='jobs.ohlcv.on_demand_ohlcv_upsert', bind=True, autoretry_for=(Exception, ), retry_backoff=True, retry_backoff_max=180, retry_jitter=True, retry_kwargs={'max_retries': 2})
def on_demand_ohlcv_upsert(self, reason: str = 'manual_run', force_backfill: bool = False) -> dict:
    """Run on-demand 1DAY OHLCV upsert for active EQ and NFO FUT instruments."""
    logger.info('Starting on-demand OHLCV upsert task. task_id={} reason={} force_backfill={}', self.request.id, reason, force_backfill)
    service = OhlcvService()
    result = service.upsert_daily_ohlcv(force_backfill=force_backfill)
    logger.info(
        'Completed on-demand OHLCV upsert task. task_id={} success={} processed={} inserted_or_updated={} errors={}',
        self.request.id,
        result.get('success', False),
        result.get('processed', 0),
        result.get('inserted_or_updated', 0),
        result.get('errors_count', 0),
    )
    result['trigger_source'] = 'on_demand'
    result['reason'] = reason
    return result


@celery_app.task(name='jobs.ohlcv.daily_ohlcv_aggregate_week', bind=True, autoretry_for=(Exception, ), retry_backoff=True, retry_backoff_max=180, retry_jitter=True, retry_kwargs={'max_retries': 2})
def daily_ohlcv_aggregate_week(self) -> dict:
    """Aggregate 1DAY OHLCV into 1WEEK OHLCV."""
    logger.info('Starting daily OHLCV weekly aggregation task')
    service = OhlcvService()
    result = service.aggregate_from_daily(target_timeframe='1WEEK')
    result['trigger_source'] = 'scheduled'
    return result


@celery_app.task(name='jobs.ohlcv.daily_ohlcv_aggregate_month', bind=True, autoretry_for=(Exception, ), retry_backoff=True, retry_backoff_max=180, retry_jitter=True, retry_kwargs={'max_retries': 2})
def daily_ohlcv_aggregate_month(self) -> dict:
    """Aggregate 1DAY OHLCV into 1MONTH OHLCV."""
    logger.info('Starting daily OHLCV monthly aggregation task')
    service = OhlcvService()
    result = service.aggregate_from_daily(target_timeframe='1MONTH')
    result['trigger_source'] = 'scheduled'
    return result
