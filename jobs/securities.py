"""Celery tasks for securities upsert (scheduled and on-demand)."""

from celery import shared_task

from services.security import SecurityService
from utils.logger import logger


@shared_task(name='jobs.securities.kite_daily_securities_upsert', bind=True, autoretry_for=(Exception, ), retry_backoff=True, retry_backoff_max=180, retry_jitter=True, retry_kwargs={'max_retries': 2})
def kite_daily_securities_upsert(self) -> dict:
    """Run daily securities upsert from Kite NFO futures and their underlyings."""
    logger.info('Starting scheduled securities upsert task')
    service = SecurityService()
    result = service.upsert_nfo_futures_and_underlyings()
    result['trigger_source'] = 'scheduled'
    return result


@shared_task(name='jobs.securities.kite_on_demand_securities_upsert', bind=True, autoretry_for=(Exception, ), retry_backoff=True, retry_backoff_max=180, retry_jitter=True, retry_kwargs={'max_retries': 2})
def kite_on_demand_securities_upsert(self, reason: str = 'manual_run') -> dict:
    """Run on-demand securities upsert from Kite NFO futures and their underlyings."""
    logger.info(f'Starting on-demand securities upsert task. Reason: {reason}')
    service = SecurityService()
    result = service.upsert_nfo_futures_and_underlyings()
    result['trigger_source'] = 'on_demand'
    result['reason'] = reason
    return result