# backend/app/integrations/discord/service.py

from typing import Any
from datetime import datetime, timezone, timedelta

from app.integrations.discord.client import DiscordClient
from app.utils.logger import get_logger
from app.schemas.notification import NotificationPayload

logger = get_logger(__name__)

_IST = timedelta(hours=5, minutes=30)

_STATUS_ICON = { "success": "✅", "warning": "⚠️", "failed": "❌", }

_STATUS_COLOR = { "success": 0x2ECC71, "warning": 0xF1C40F, "failed": 0xE74C3C, }


class DiscordNotificationService:
    """Service to send notifications to Discord channels."""

    def __init__(self, client: DiscordClient):
        self.client = client

    def send_notification(self, payload: NotificationPayload) -> None:
        try:
            embed = self._render(payload)
            self.client.send_message(embeds=[embed])
        except Exception as e:
            logger.exception(f"Failed to send notification to Discord: {e}")

    @staticmethod
    def _esc(text: str) -> str:
        return str(text).replace("`", "'")

    def _render(self, payload: NotificationPayload) -> dict[str, Any]:
        icon = _STATUS_ICON.get(payload.status, "ℹ️")
        color = _STATUS_COLOR.get(payload.status, 0x95A5A6)

        now_utc = datetime.now(timezone.utc)
        now_ist = now_utc + _IST
        time_str = now_ist.strftime("%d %b %Y, %H:%M IST")

        footer_parts = [time_str]
        if payload.duration_seconds > 0:
            footer_parts.insert(0, f"{payload.duration_seconds:.1f}s")

        embed: dict[str, Any] = { "author": { "name": "ATLAS"}, "title": f"{icon}  {payload.operation}", "description": self._esc(payload.summary), "color": color, "timestamp": now_utc.isoformat(), "footer": { "text": "  ·  ".join(footer_parts) }, "fields": [], }

        for metric in payload.results:
            # Short values go inline (Discord shows up to 3 per row); long ones span full width
            inline = len(self._esc(metric.value)) <= 40
            embed["fields"].append({ "name": metric.label, "value": self._esc(metric.value), "inline": inline, })

        if payload.warnings:
            embed["fields"].append({ "name": "⚠️  Warnings", "value": "\n".join(f"• {self._esc(w)}" for w in payload.warnings), "inline": False, })

        if payload.action_required:
            embed["fields"].append({ "name": "📋  Action Required", "value": "\n".join(f"• {self._esc(a)}" for a in payload.action_required), "inline": False, })

        return embed
