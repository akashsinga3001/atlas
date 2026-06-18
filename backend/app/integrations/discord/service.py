# backend/app/integrations/discord/service.py

from typing import Any

from app.integrations.discord.client import DiscordClient
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DiscordNotificationService:
    """Service to send notifications to Discord channels."""

    def __init__(self, client: DiscordClient):
        self.client = client

    def notify_task_success(self, task_name: str, duration_seconds: float, result: dict[str, Any]) -> None:
        """Sends a notification to Discord when a task completes successfully."""
        try:
            lines = [ f"✅ {task_name}", "", f"Duration: {duration_seconds:.2f}s", ]
            self._append_summary(lines, result.get("data"), )
            self.client.send_message("\n".join(lines))
        except Exception:
            logger.exception(f"Failed sending success notification for {task_name}")

    def notify_task_failure(self, task_name: str, duration_seconds: float, exception: Exception, ) -> None:
        try:
            message = (f"❌ {task_name}\n\n"
                       f"Duration: {duration_seconds:.2f}s\n"
                       f"Exception: {type(exception).__name__}\n"
                       f"Message: {str(exception)}")

            self.client.send_message(message)

        except Exception:
            logger.exception(f"Failed sending failure notification for {task_name}")

    def _append_summary(self, lines: list[str], data: Any, ) -> None:
        if not isinstance(data, dict):
            return

        if "count" in data:
            lines.append(f"Count: {data['count']}")

        if "loaded_tickers" in data:
            lines.append(f"Loaded Tickers: {data['loaded_tickers']}")

        if "processed_securities" in data:
            lines.append(f"Processed Securities: {data['processed_securities']}")

        if "total_candles" in data:
            lines.append(f"Total Candles: {data['total_candles']:,}")

        if "persisted_candles" in data:
            lines.append(f"Persisted Candles: {data['persisted_candles']:,}")

        if "failed_tickers" in data:
            lines.append(f"Failed Tickers: {len(data['failed_tickers'])}")
