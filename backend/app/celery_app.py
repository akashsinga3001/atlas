# backend/app/celery_app.py

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery('atlas')

beat_schedule = { 'kite-daily-token-refresh-08:45': { 'task': 'app.jobs.refresh_broker_token.refresh_kite_token', 'schedule': crontab(hour=8, minute=45) } }

celery_app.conf.update(broker_url=settings.REDIS_URL, result_backend=settings.REDIS_URL, include=['app.jobs.refresh_broker_token'], task_serializer='json', result_serializer='json', accept_content=['json'], timezone="Asia/Kolkata", task_always_eager=False, beat_schedule=beat_schedule)

celery_app.autodiscover_tasks(['app.jobs'])
