# backend/app/celery_app.py

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery('atlas')

beat_schedule = { 'kite-daily-token-refresh-07:45': { 'task': 'app.jobs.refresh_broker_token.refresh_kite_token', 'schedule': crontab(hour=7, minute=45) }, 'securities-daily-import-08:00': { 'task': 'app.jobs.securities_import.import_securities', 'schedule': crontab(hour=8, minute=00) } }

celery_app.conf.update(broker_url=settings.REDIS_URL, result_backend=settings.REDIS_URL, include=[ 'app.jobs.refresh_broker_token', 'app.jobs.securities_import', 'app.jobs.ohlcv_import'], task_serializer='json', result_serializer='json', accept_content=['json'], timezone="Asia/Kolkata", task_always_eager=False, beat_schedule=beat_schedule, broker_connection_retry_on_startup=True)

celery_app.autodiscover_tasks(['app.jobs'])
