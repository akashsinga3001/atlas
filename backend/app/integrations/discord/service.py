# backend/app/integrations/discord/service.py

from typing import Any
from datetime import datetime, timezone

from app.integrations.discord.client import DiscordClient
from app.utils.logger import get_logger
from app.schemas.notification import NotificationPayload

logger = get_logger(__name__)


class DiscordNotificationService:
    """Service to send notifications to Discord channels."""
    _WIDTH_RULE = "─" * 42  # fixed-width line; pins embed card width across all job types

    STATUS_COLOR = {
        "success": 0x2ECC71,  # green
        "warning": 0xF1C40F,  # yellow
        "failed": 0xE74C3C,  # red
    }

    def __init__(self, client: DiscordClient):
        self.client = client

    def send_notification(self, payload: NotificationPayload) -> None:
        """Send a notification to the configured Discord channel."""
        try:
            embed = self._render(payload)
            self.client.send_message(embeds=[embed])
        except Exception as e:
            logger.exception(f"Failed to send notification to Discord: {e}")

    @staticmethod
    def _escape_code(text: str) -> str:
        """Escape backticks so dynamic text can't break inline code or code-block formatting."""
        return str(text).replace("`", "'")

    def _render(self, payload: NotificationPayload) -> dict[str, Any]:
        """Render the notification payload into a Discord embed."""
        color = self.STATUS_COLOR.get(payload.status, 0x95A5A6)  # grey fallback
        timestamp = datetime.now(timezone.utc).isoformat()

        embed: dict[str, Any] = { "title": "ATLAS", "description": f"**{payload.operation}**\n{self._WIDTH_RULE}", "color": color, "timestamp": timestamp, "footer": { "text": "Atlas Notifications"}, "fields": [{ "name": "Summary", "value": f"`{self._escape_code(payload.summary)}`", "inline": False }, { "name": "Status", "value": f"`{payload.status.upper()}`", "inline": True }, { "name": "Duration", "value": f"`{payload.duration_seconds:.2f}s`", "inline": True }] }

        if payload.results:
            label_width = max(len(metric.label) for metric in payload.results)
            rows = "\n".join(f"{self._escape_code(metric.label).ljust(label_width+12)}  {self._escape_code(metric.value)}" for metric in payload.results)
            embed["fields"].append({ "name": "Results", "value": f"```\n{rows}\n```", "inline": False, })

        if payload.warnings:
            rows = "\n".join(f"⚠ {self._escape_code(w)}" for w in payload.warnings)
            embed["fields"].append({ "name": "Warnings", "value": f"```\n{rows}\n```", "inline": False, })

        if payload.action_required:
            rows = "\n".join(f"→ {self._escape_code(a)}" for a in payload.action_required)
            embed["fields"].append({ "name": "Action Required", "value": f"```\n{rows}\n```", "inline": False, })

        return embed
