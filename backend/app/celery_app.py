# backend/app/celery_app.py

from celery import Celery
from celery.schedules import crontab

from app.core.celery_schedule import beat_schedule
from app.core.config import settings

celery_app = Celery('atlas')

celery_app.conf.update(broker_url=settings.REDIS_URL, result_backend=settings.REDIS_URL, include=[ 'app.jobs.refresh_broker_token', 'app.jobs.securities_import', 'app.jobs.ohlcv_import', 'app.jobs.enrich_securities'], task_serializer='json', result_serializer='json', accept_content=['json'], timezone="Asia/Kolkata", enable_utc=False, task_always_eager=False, beat_schedule=beat_schedule, broker_connection_retry_on_startup=True)

celery_app.autodiscover_tasks(['app.jobs'])
