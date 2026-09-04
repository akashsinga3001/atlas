# backend/app/celery_app.py

from celery import Celery

from app.core.config import settings
from app.strategies.bootstrap import register_strategies
from app.exit_evaluators.bootstrap import register_exit_evaluators
from app.execution_engines.bootstrap import register_execution_engines

register_strategies()
register_exit_evaluators()
register_execution_engines()

celery_app = Celery('atlas')

celery_app.conf.update(
    broker_url=settings.REDIS_URL,
    result_backend=settings.REDIS_URL,
    include=[ 'app.jobs.refresh_broker_token', 'app.jobs.securities_import', 'app.jobs.ohlcv_import', 'app.jobs.enrich_securities', 'app.jobs.feature_generation', 'app.jobs.strategy_execution', 'app.jobs.position_sync', 'app.jobs.trade_entry', 'app.jobs.trade_exit', 'app.jobs.trade_reconciliation',
              'app.jobs.option_chain_import', ],
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    timezone="Asia/Kolkata",
    enable_utc=False,
    task_always_eager=False,
    # Beat's schedule is DB-driven (schedule_entries table) via RedBeat — see
    # app/services/schedule.py / app/services/schedule_redis_sync.py. Nothing here
    # is "static" from RedBeat's perspective, so its own startup cleanup logic
    # never fights with entries created/edited through the /schedule API.
    beat_schedule={},
    broker_connection_retry_on_startup=True,
    # Allow long-running jobs (historical OHLCV, enrichment) up to 12 hours
    # before Redis re-queues the task assuming the worker died.
    broker_transport_options={ "visibility_timeout": 43200 },
    # feature_generation is the only job with no broker/Selenium dependency that has
    # actually shown recurring OOM kills (unbounded full-history loads across 635
    # securities every 10-minute live-refresh run). Routing it to its own queue/worker
    # means a memory spike there can never take down a Chrome session another job
    # (trade_entry, position_sync, etc.) has open in the shared default worker.
    task_default_queue="celery",
    task_routes={ "app.jobs.feature_generation.*": { "queue": "features" } },
)

celery_app.autodiscover_tasks(['app.jobs'])
