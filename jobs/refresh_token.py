"""Celery tasks for Kite token refresh (scheduled and on-demand)."""

from datetime import datetime, timezone

from celery_app import celery_app

from services.brokers.kite import KiteService
from utils.logger import logger


def _run_refresh(trigger_source: str) -> dict:
    """Run token refresh once while reusing broker-level distributed lock behavior."""
    service = KiteService()
    result = service.ensure_valid_token(force_refresh=True)
    result['trigger_source'] = trigger_source
    result['timestamp'] = datetime.now(timezone.utc).isoformat()
    result['skipped'] = False
    return result


@celery_app.task(name='jobs.refresh_token.kite_daily_refresh', bind=True, autoretry_for=(Exception, ), retry_backoff=True, retry_backoff_max=300, retry_jitter=True, retry_kwargs={'max_retries': 3})
def kite_daily_refresh(self) -> dict:
    """Run scheduled Kite token refresh at fixed daily time."""
    logger.info('Starting scheduled Kite token refresh task')
    return _run_refresh(trigger_source='scheduled')


@celery_app.task(name='jobs.refresh_token.kite_on_demand_refresh', bind=True, autoretry_for=(Exception, ), retry_backoff=True, retry_backoff_max=120, retry_jitter=True, retry_kwargs={'max_retries': 2})
def kite_on_demand_refresh(self, reason: str = 'token_expired') -> dict:
    """Run on-demand Kite token refresh when broker reports expiry errors."""
    logger.info(f'Starting on-demand Kite token refresh task. Reason: {reason}')
    result = _run_refresh(trigger_source='on_demand')
    result['reason'] = reason
    return result
