# backend/app/integrations/discord/client.py

import httpx

from app.utils.logger import get_logger

logger = get_logger(__name__)


class DiscordClient:
    """A client for interacting with the Discord API."""

    def __init__(self, webhook_url: str, timeout: int = 10):
        self._webhook_url = webhook_url
        self._timeout = timeout

    def send_message(self, content: str) -> None:
        """Sends a message to the Discord channel via the webhook."""
        logger.info(f"Sending Discord Notification")
        response = httpx.post(self._webhook_url, json={ "content": content }, timeout=self._timeout)
        response.raise_for_status()
