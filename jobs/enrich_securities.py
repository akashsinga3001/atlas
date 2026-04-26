"""Celery tasks for securities enrichment from screener.in."""

import time
from datetime import datetime
from typing import Any

from celery import shared_task

from services.screener import ScreenerService
from services.security import SecurityService
from utils.logger import logger


DEFAULT_BATCH_SIZE = 50


def _validate_batch_size(batch_size: int) -> int:
    """Validate that batch size is a positive integer."""
    if batch_size < 1:
        raise ValueError('batch_size must be >= 1')
    return batch_size


def _run_securities_enrichment(batch_size: int = DEFAULT_BATCH_SIZE) -> dict[str, Any]:
    """Enrich active EQ securities missing any classification field from screener.in."""
    batch_size = _validate_batch_size(batch_size)
    started_at = datetime.utcnow()
    security_service = SecurityService()
    screener_service = ScreenerService()

    result: dict[str, Any] = {
        'success': True,
        'total_found': 0,
        'enriched': 0,
        'not_found': 0,
        'failed': 0,
        'batch_size': batch_size,
        'mode': 'incremental_missing_classification',
    }

    try:
        securities = security_service.get_eq_securities_needing_enrichment(limit=None)
        result['total_found'] = len(securities)

        if not securities:
            logger.info('No EQ securities need enrichment')
            result['execution_duration_seconds'] = int((datetime.utcnow() - started_at).total_seconds())
            return result

        total_batches = (len(securities) + batch_size - 1) // batch_size
        logger.info(
            'Starting securities enrichment run. total={} batch_size={} batches={}',
            len(securities),
            batch_size,
            total_batches,
        )

        for batch_index in range(0, len(securities), batch_size):
            batch = securities[batch_index:batch_index + batch_size]
            batch_number = (batch_index // batch_size) + 1
            logger.info('Processing enrichment batch {}/{} size={}', batch_number, total_batches, len(batch))

            for security in batch:
                try:
                    scraped = screener_service.scrape_company_enrichment(
                        ticker=security.ticker,
                        display_name=security.display_name or security.ticker,
                    )

                    if not scraped:
                        result['not_found'] += 1
                        continue

                    updated = security_service.update_missing_enrichment_fields(
                        security_id=security.id,
                        enrichment_data=scraped,
                    )

                    if updated:
                        result['enriched'] += 1
                    else:
                        result['not_found'] += 1
                except Exception as exc:
                    logger.error('Failed enrichment for {}: {}', security.ticker, exc)
                    result['failed'] += 1
                finally:
                    time.sleep(0.35)

        result['execution_duration_seconds'] = int((datetime.utcnow() - started_at).total_seconds())
        logger.info(
            'Securities enrichment completed. total={} enriched={} not_found={} failed={} duration={}s',
            result['total_found'],
            result['enriched'],
            result['not_found'],
            result['failed'],
            result['execution_duration_seconds'],
        )
        return result
    except Exception as exc:
        logger.error('Securities enrichment job failed: {}', exc)
        result['success'] = False
        result['error'] = str(exc)
        result['execution_duration_seconds'] = int((datetime.utcnow() - started_at).total_seconds())
        return result
    finally:
        screener_service.close()


@shared_task(name='jobs.enrich_securities.daily_securities_enrichment', bind=True, autoretry_for=(Exception, ), retry_backoff=True, retry_backoff_max=180, retry_jitter=True, retry_kwargs={'max_retries': 2})
def daily_securities_enrichment(self, batch_size: int = DEFAULT_BATCH_SIZE) -> dict[str, Any]:
    """Run scheduled daily securities enrichment for missing classification fields."""
    logger.info('Starting scheduled securities enrichment task')
    result = _run_securities_enrichment(batch_size=batch_size)
    result['trigger_source'] = 'scheduled'
    return result


@shared_task(name='jobs.enrich_securities.on_demand_securities_enrichment', bind=True, autoretry_for=(Exception, ), retry_backoff=True, retry_backoff_max=180, retry_jitter=True, retry_kwargs={'max_retries': 2})
def on_demand_securities_enrichment(self, reason: str = 'manual_run', batch_size: int = DEFAULT_BATCH_SIZE) -> dict[str, Any]:
    """Run on-demand securities enrichment for missing classification fields."""
    logger.info('Starting on-demand securities enrichment task. Reason: {}', reason)
    result = _run_securities_enrichment(batch_size=batch_size)
    result['trigger_source'] = 'on_demand'
    result['reason'] = reason
    return result
