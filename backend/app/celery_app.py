# backend/app/celery_app.py

from celery import Celery
from app.core.config import settings

celery = Celery(
    'atlas',
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[]
)

celery.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    beat_scheduler='redbeat.RedBeatScheduler',
    redbeat_redis_url=settings.REDIS_URL,
)