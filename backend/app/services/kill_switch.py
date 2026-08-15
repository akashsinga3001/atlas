# backend/app/services/kill_switch.py

from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.kill_switch import KillSwitch
from app.repositories.kill_switch import KillSwitchRepository
from app.schemas.kill_switch import KillSwitchResponse
from app.utils.logger import get_logger

logger = get_logger(__name__)


class KillSwitchService:
    """Service for reading and toggling the global new-entry kill switch."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = KillSwitchRepository(db)

    def get_status(self) -> dict:
        """Return the current kill-switch state."""
        return self._build_response(self.repo.get_singleton())

    def activate(self, reason: str) -> dict:
        """Pause new-entry jobs and send a Discord alert."""
        entry = self.repo.update(self.repo.get_singleton(), { "enabled": True, "reason": reason, "activated_at": datetime.now(timezone.utc) })
        self._notify(activated=True, reason=reason)
        return self._build_response(entry)

    def deactivate(self) -> dict:
        """Resume new-entry jobs and send a Discord alert."""
        entry = self.repo.update(self.repo.get_singleton(), { "enabled": False, "reason": None, "activated_at": None })
        self._notify(activated=False, reason=None)
        return self._build_response(entry)

    def _build_response(self, entry: KillSwitch) -> dict:
        """Serialise the kill-switch row to a dict."""
        return KillSwitchResponse(enabled=entry.enabled, reason=entry.reason, activated_at=entry.activated_at, updated_at=entry.updated_at).model_dump()

    def _notify(self, activated: bool, reason: str | None) -> None:
        """Send a Discord alert on activation/deactivation — a state change this consequential should page you."""
        try:
            from app.celery.base import get_discord_service
            from app.schemas.notification import NotificationPayload, NotificationMetric
            discord = get_discord_service()
            if not discord:
                return
            if activated:
                payload = NotificationPayload(operation="Kill Switch", status="warning", duration_seconds=0, summary="New-entry jobs paused. Existing positions' exits and trailing stops are unaffected.", results=[NotificationMetric(label="Reason", value=reason or "—")], action_required=["Resume from the Atlas UI when ready."])
            else:
                payload = NotificationPayload(operation="Kill Switch", status="success", duration_seconds=0, summary="New-entry jobs resumed.", results=[])
            discord.send_notification(payload)
        except Exception:
            logger.warning("Failed to send kill switch Discord alert.", exc_info=True)
