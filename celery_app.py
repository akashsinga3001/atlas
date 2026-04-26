"""
Celery application configuration for background task processing.
"""

from celery import Celery

from config import settings


celery_app = Celery('atlas')

broker_url = settings.CELERY_BROKER_URL or settings.REDIS_URL
result_backend = settings.CELERY_RESULT_BACKEND or settings.REDIS_URL

celery_app.conf.update(
	broker_url=broker_url,
	result_backend=result_backend,
	include=['jobs.health_check'],
	task_serializer='json',
	result_serializer='json',
	accept_content=['json'],
	timezone=settings.CELERY_TIMEZONE,
	enable_utc=settings.CELERY_ENABLE_UTC,
	task_always_eager=settings.CELERY_TASK_ALWAYS_EAGER,
	beat_schedule={}
)

celery_app.autodiscover_tasks(['jobs'])
