"""
Celery application configuration for background task processing.
"""

from celery import Celery
from celery.schedules import crontab
from celery.signals import beat_init

from config import settings