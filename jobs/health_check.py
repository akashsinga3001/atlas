"""Minimal Celery task definitions used for worker health validation."""

from celery_app import celery_app


@celery_app.task(name='jobs.health_check.ping')
def ping() -> str:
    return 'pong'
