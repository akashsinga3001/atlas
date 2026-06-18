# backend/app/integrations/discord/service.py

from typing import Any
from datetime import datetime

from app.integrations.discord.client import DiscordClient
from app.utils.logger import get_logger
from app.schemas.notification import NotificationPayload

logger = get_logger(__name__)


class DiscordNotificationService:
    """Service to send notifications to Discord channels."""

    def __init__(self, client: DiscordClient):
        self.client = client

    def send_notification(self, payload: NotificationPayload) -> None:
        """Send a notification to the configured Discord channel."""
        try:
            message = self._render(payload)
            self.client.send_message(message)
        except Exception as e:
            logger.exception(f"Failed to send notification to Discord: {e}")

    def _render(self, payload: NotificationPayload) -> str:
        """Render the notification payload into a Discord message format."""
        status_icon = { "success": "🟢", "warning": "🟡", "failed": "🔴"}.get(payload.status, "ℹ️")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        lines = [ f"{status_icon} ATLAS OPERATION", "", f"Operation : {payload.operation}", f"Status    : {payload.status.upper()}", f"Duration  : {payload.duration_seconds:.2f}s", f"Time      : {timestamp}", "", "Summary", "-------", payload.summary ]

        if payload.results:
            lines.extend([ "", "Results", "-------"])

            for metric in payload.results:
                lines.append(f"•{metric['label']}: {metric['value']}")

        if payload.warnings:
            lines.extend([ "", "Warnings", "-------"])

            for warning in payload.warnings:
                lines.append(f"• {warning}")

        if payload.action_required:
            lines.extend([ "", "Action Required", "-------", payload.action_required ])

            for action in payload.action_required:
                lines.append(f"• {action}")

        return "\n".join(lines)
