# backend/app/celery_app.py

from celery import Celery

from app.core.celery_schedule import beat_schedule
from app.core.config import settings
from app.strategies.bootstrap import register_strategies
from app.exit_evaluators.bootstrap import register_exit_evaluators

register_strategies()
register_exit_evaluators()

celery_app = Celery('atlas')

celery_app.conf.update(
    broker_url=settings.REDIS_URL,
    result_backend=settings.REDIS_URL,
    include=[ 'app.jobs.refresh_broker_token', 'app.jobs.securities_import', 'app.jobs.ohlcv_import', 'app.jobs.enrich_securities', 'app.jobs.feature_generation', 'app.jobs.strategy_execution', 'app.jobs.position_sync', 'app.jobs.trade_entry', 'app.jobs.trade_exit', 'app.jobs.trade_reconciliation', ],
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    timezone="Asia/Kolkata",
    enable_utc=False,
    task_always_eager=False,
    beat_schedule=beat_schedule,
    broker_connection_retry_on_startup=True,
    # Allow long-running jobs (historical OHLCV, enrichment) up to 12 hours
    # before Redis re-queues the task assuming the worker died.
    broker_transport_options={ "visibility_timeout": 43200 },
)

celery_app.autodiscover_tasks(['app.jobs'])
