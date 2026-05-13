"""HTTP client for routing orders to an external order service."""

from __future__ import annotations

from typing import Any

import requests

from config import settings
from services.brokers.kite import KiteService


class OrderRoutingService:
    """Routes order requests to an external API endpoint."""

    def __init__(self) -> None:
        self._base_url = str(settings.ORDER_SERVICE_BASE_URL).strip().rstrip('/')
        self._timeout = int(settings.ORDER_SERVICE_TIMEOUT_SECONDS)
        self._route_path = str(settings.ORDER_SERVICE_ROUTE_PATH).strip()
        self._default_variety = str(settings.ORDER_SERVICE_ORDER_VARIETY).strip() or 'regular'
        self._session = requests.Session()
        self._kite_service = KiteService()

    def is_configured(self) -> bool:
        """Return True when base URL is configured."""
        return bool(self._base_url)

    def route_single_order(self, order: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        """Submit a single order and return (success, response). Never raises."""
        variety = str(order.get('variety', self._default_variety)).strip() or self._default_variety
        payload = dict(order.get('order', {}))
        if not payload:
            return False, {'success': False, 'error': 'missing order payload'}

        path = f"{self._route_path.rstrip('/')}/{variety}"
        try:
            result = self._request('POST', path, json_payload=payload)
        except Exception as exc:
            return False, {'success': False, 'error': str(exc)}

        if isinstance(result, dict) and result.get('order_id'):
            return True, result

        return False, {'success': False, 'error': 'no order_id in response', 'response': result}

    def route_orders(self, orders: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Submit regular orders one by one to /orders/<variety>."""
        responses: list[dict[str, Any]] = []
        for order in orders:
            success, result = self.route_single_order(order)
            responses.append({'request': order, 'response': result, 'success': success})
        return responses

    def _request(self, method: str, path: str, json_payload: dict[str, Any] | None = None) -> Any:
        """Perform authenticated request using current Kite access token."""
        if not self._base_url:
            raise ValueError('ORDER_SERVICE_BASE_URL is not configured')

        self._kite_service.ensure_valid_token()
        access_token = self._kite_service.get_access_token()
        if not access_token:
            raise ValueError('Kite access token is unavailable for order routing')

        normalized_path = path if path.startswith('/') else f'/{path}'
        url = f'{self._base_url}{normalized_path}'
        headers = {
            'Accept': 'application/json',
            'Authorization': f'Bearer {access_token}',
        }

        response = self._session.request(method=method, url=url, json=json_payload, timeout=self._timeout, headers=headers)
        response.raise_for_status()

        if not response.content:
            return {}

        content_type = response.headers.get('Content-Type', '')
        if 'application/json' in content_type.lower():
            return response.json()

        return {'raw': response.text}
