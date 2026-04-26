"""Minimal Celery task definitions used for worker health validation."""

from celery import shared_task


@shared_task(name='jobs.health_check.ping')
def ping() -> str:
    return 'pong'
