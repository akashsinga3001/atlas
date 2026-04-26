"""
Celery application configuration for background task processing.
"""

from celery import Celery
from celery.schedules import crontab

from config import settings

celery_app = Celery('atlas')

broker_url = settings.CELERY_BROKER_URL or settings.REDIS_URL
result_backend = settings.CELERY_RESULT_BACKEND or settings.REDIS_URL

celery_app.conf.update(
    broker_url=broker_url,
    result_backend=result_backend,
    include=['jobs.health_check', 'jobs.refresh_token', 'jobs.securities', 'jobs.enrich_securities', 'jobs.ohlcv', 'jobs.features'],
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    timezone=settings.CELERY_TIMEZONE,
    enable_utc=settings.CELERY_ENABLE_UTC,
    task_always_eager=settings.CELERY_TASK_ALWAYS_EAGER,
    beat_schedule={
        'kite-daily-securities-upsert-0655': {
            'task': 'jobs.securities.kite_daily_securities_upsert',
            'schedule': crontab(hour=6, minute=55)
        },
        'screener-daily-securities-enrichment-0715': {
            'task': 'jobs.enrich_securities.daily_securities_enrichment',
            'schedule': crontab(hour=7, minute=15)
        },
        'kite-daily-token-refresh-0755': {
            'task': 'jobs.refresh_token.kite_daily_refresh',
            'schedule': crontab(hour=7, minute=55)
        },
        'ohlcv-daily-upsert-1600': {
            'task': 'jobs.ohlcv.daily_ohlcv_pipeline',
            'schedule': crontab(hour=16, minute=0)
        }
    }
)

celery_app.autodiscover_tasks(['jobs'])
