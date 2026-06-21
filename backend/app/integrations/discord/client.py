# backend/app/integrations/discord/client.py

from typing import Any

import httpx

from app.utils.logger import get_logger

logger = get_logger(__name__)


class DiscordClient:
    """A client for interacting with the Discord API."""

    def __init__(self, webhook_url: str, timeout: int = 10):
        self._webhook_url = webhook_url
        self._timeout = timeout

    def send_message(self, content: str | None = None, embeds: list[dict[str, Any]] | None = None, ) -> None:
        """Sends a message to the Discord channel via the webhook."""
        if not content and not embeds:
            raise ValueError("send_message requires at least one of: content, embeds")

        payload: dict[str, Any] = {}
        if content:
            payload["content"] = content
        if embeds:
            payload["embeds"] = embeds

        logger.info("Sending Discord Notification")
        response = httpx.post(self._webhook_url, json=payload, timeout=self._timeout)
        response.raise_for_status()
