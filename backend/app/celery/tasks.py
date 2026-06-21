# backend/app/celery/tasks.py

import time
from enum import Enum as PythonEnum

from celery import Task

from app.core.config import settings
from app.integrations.discord.client import DiscordClient
from app.integrations.discord.service import DiscordNotificationService
from app.utils.logger import get_logger
from app.schemas.notification import NotificationPayload, NotificationMetric

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

    def get_display_name(self, kwargs: dict) -> str:
        """Get the display name of the task."""
        return self.display_name or self.name

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

        duration = self._get_duration()
        payload = self.build_success_notification(duration_seconds=duration, result=retval, args=args, kwargs=kwargs)
        discord_service.send_notification(payload)

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Send a notification to Discord if the task failed."""
        policy = self.get_notification_policy(args, kwargs)

        if policy not in [NotificationPolicy.ALWAYS, NotificationPolicy.ON_FAILURE, NotificationPolicy.ON_SUCCESS_OR_FAILURE, NotificationPolicy.ON_SUCCESS_AND_FAILURE]:
            return

        discord_service = get_discord_service()

        if not discord_service:
            logger.warning("Discord service is not available. Skipping failure notification.")
            return

        duration = self._get_duration()
        payload = self.build_failure_notification(duration_seconds=duration, exception=exc, args=args, kwargs=kwargs)
        discord_service.send_notification(payload)

    def _get_duration(self) -> float:
        """Calculate the duration of the task in seconds."""
        started_at = getattr(self.request, "atlas_started_at", time.time(), )
        return round(time.time() - started_at, 2)

    def build_success_notification(self, duration_seconds: float, result: dict, args, kwargs, ) -> NotificationPayload:
        """Build the notification payload for a successful task."""
        return NotificationPayload(operation=self.get_display_name(kwargs), status="success", duration_seconds=duration_seconds, summary=result.get("message", "Operation completed successfully.", ), )

    def build_failure_notification(self, duration_seconds: float, exception: Exception, args, kwargs, ) -> NotificationPayload:
        """Build the notification payload for a failed task."""
        return NotificationPayload(operation=self.get_display_name(kwargs), status="failed", duration_seconds=duration_seconds, summary=str(exception), action_required=["Review logs for additional details."], )


# Task Class ExampleTask(AtlasTask):


class BrokerTokenRefreshTask(AtlasTask):
    display_name = "Broker Token Refresh"


class SecuritiesImportTask(AtlasTask):
    display_name = "Securities Import"


class SecuritiesEnrichmentTask(AtlasTask):
    display_name = "Securities Enrichment"

    def build_success_notification(self, duration_seconds: float, result: dict, args, kwargs) -> NotificationPayload:
        """Build the notification payload for a successful securities enrichment task."""
        data = result.get("data", {})
        return NotificationPayload(
            operation=self.get_display_name(kwargs), status="success", duration_seconds=duration_seconds, summary="Securities enrichment completed.", results=[NotificationMetric(label="Enriched Securities", value=str(data.get("enriched_securities", 0))),
                                                                                                                                                               NotificationMetric(label="Failed Securities", value=str(len(data.get("failed_securities", [])))),
                                                                                                                                                               NotificationMetric(label="Partial Securities", value=str(len(data.get("partial_securities", []))))], warnings=["Some securities may have incomplete data. Review the results for details."] if data.get("partial_securities") else []
        )


class OHLCVImportTask(AtlasTask):
    display_name = "OHLCV Import"

    def get_notification_policy(self, args: tuple, kwargs: dict) -> NotificationPolicy:
        """Get the notification policy for the task."""
        task_type = kwargs.get("type", None)

        if task_type == "live_refresh":
            return NotificationPolicy.ON_FAILURE

        return NotificationPolicy.ON_SUCCESS_AND_FAILURE

    def get_display_name(self, kwargs: dict, ) -> str:
        """Set the display name based on the task type."""
        task_type = kwargs.get("type")

        if task_type == "historical":
            return "OHLCV Historical Import"

        if task_type == "incremental":
            return "OHLCV Incremental Sync"

        if task_type == "live_refresh":
            return "OHLCV Live Refresh"

        return self.display_name

    def build_success_notification(self, duration_seconds: float, result: dict, args, kwargs, ) -> NotificationPayload:
        """Build the notification payload for a successful OHLCV import task."""
        data = result.get("data", {})
        return NotificationPayload(operation=self.get_display_name(kwargs), status="success", duration_seconds=duration_seconds, summary="OHLCV synchronization completed.", results=[NotificationMetric(label="Loaded Tickers", value=str(data.get("loaded_tickers", 0))), NotificationMetric(label="Persisted Candles", value=str(data.get("persisted_candles", 0))), NotificationMetric(label="Failed Tickers", value=str(len(data.get("failed_tickers", []))))])


class FeatureGenerationTask(AtlasTask):
    display_name = "Feature Generation"
