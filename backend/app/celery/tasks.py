# backend/app/celery/tasks.py

import time
from enum import Enum as PythonEnum

from celery import Task

from app.core.config import settings
from app.integrations.discord.client import DiscordClient
from app.integrations.discord.service import DiscordNotificationService
from app.utils.logger import get_logger

logger = get_logger(__name__)


class NotificationPolicy(PythonEnum):
    """Notification policy for Discord notifications."""
    ALWAYS = "always"
    NONE = "none"
    ON_FAILURE = "on_failure"
    ON_SUCCESS = "on_success"
    ON_SUCCESS_OR_FAILURE = "on_success_or_failure"
    ON_SUCCESS_AND_FAILURE = "on_success_and_failure"


_discord_service: DiscordNotificationService | None = None


def get_discord_service() -> DiscordNotificationService | None:
    global _discord_service

    if not settings.DISCORD_ENABLED:
        return None

    if not settings.DISCORD_WEBHOOK_URL:
        logger.warning("Discord webhook URL is not set. Discord notifications will be disabled.")
        return None

    if _discord_service is None:
        _discord_service = DiscordNotificationService(DiscordClient(settings.DISCORD_WEBHOOK_URL))

    return _discord_service


class AtlasTask(Task):
    abstract = True
    display_name: str | None = None

    def get_notification_policy(self, args: tuple, kwargs: dict) -> NotificationPolicy:
        """Get the notification policy for the task."""
        return NotificationPolicy.ON_SUCCESS_AND_FAILURE

    def before_start(self, task_id, args, kwargs):
        """Record the start time of the task."""
        self.request.atlas_started_at = time.time()

    def on_success(self, retval, task_id, args, kwargs):
        """Send a notification to Discord if the task succeeded."""
        policy = self.get_notification_policy(args, kwargs)

        if policy not in [NotificationPolicy.ALWAYS, NotificationPolicy.ON_SUCCESS, NotificationPolicy.ON_SUCCESS_OR_FAILURE, NotificationPolicy.ON_SUCCESS_AND_FAILURE]:
            return

        discord_service = get_discord_service()

        if not discord_service:
            logger.warning("Discord service is not available. Skipping success notification.")
            return

        discord_service.notify_task_success(task_name=self.display_name or self.name, duration_seconds=self._get_duration(), result=retval)

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Send a notification to Discord if the task failed."""
        policy = self.get_notification_policy(args, kwargs)

        if policy not in [NotificationPolicy.ALWAYS, NotificationPolicy.ON_FAILURE, NotificationPolicy.ON_SUCCESS_OR_FAILURE, NotificationPolicy.ON_SUCCESS_AND_FAILURE]:
            return

        discord_service = get_discord_service()

        if not discord_service:
            logger.warning("Discord service is not available. Skipping failure notification.")
            return

        discord_service.notify_task_failure(task_name=self.display_name or self.name, duration_seconds=self._get_duration(), exception=exc)

    def _get_duration(self) -> float:
        """Calculate the duration of the task in seconds."""
        started_at = getattr(self.request, "atlas_started_at", time.time(), )
        return round(time.time() - started_at, 2)


# Task Class ExampleTask(AtlasTask):


class BrokerTokenRefreshTask(AtlasTask):
    display_name = "Broker Token Refresh"


class SecuritiesImportTask(AtlasTask):
    display_name = "Securities Import"


class OHLCVImportTask(AtlasTask):
    display_name = "OHLCV Import"

    def get_notification_policy(self, args: tuple, kwargs: dict) -> NotificationPolicy:
        """Get the notification policy for the task."""
        task_type = kwargs.get("task_type", None)

        if task_type == "live_refresh":
            return NotificationPolicy.ON_FAILURE

        return NotificationPolicy.ON_SUCCESS_AND_FAILURE
