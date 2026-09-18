# backend/app/services/brokers/kite.py

import json
import time
from datetime import datetime, timedelta
from threading import Lock
from typing import Any, Callable, Dict
from urllib.parse import parse_qs, urlparse
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

import httpx
import requests
from kiteconnect import KiteConnect
from kiteconnect.exceptions import TokenException
from redis import Redis
from redis.exceptions import RedisError

import pyotp
import pandas as pd

from app.core.config import settings
from app.core.exceptions import ExternalAPIError
from app.enums.security import SecurityType
from app.utils.logger import get_logger
from app.services.selenium import SeleniumService
from app.schemas.base import SuccessResponse

logger = get_logger(__name__)


class KiteService:
    """Service class to interact with the Kite Connect API and manage authentication, token refresh, and data retrieval."""

    TOKEN_CACHE_KEY = "kite:access_token"
    TOKEN_CACHE_TTL_SECONDS = 24 * 60 * 60  # 24 hours

    def __init__(self):
        self._token_expires_at: datetime | None = None
        self._token_lock = Lock()
        self._redis_client = self._build_redis_client()
        self.api_key = settings.KITE_API_KEY
        self.api_secret = settings.KITE_API_SECRET
        self.kite = KiteConnect(api_key=self.api_key)
        self.selenium_service: SeleniumService | None = None

        cached_payload = self._get_cached_token()
        if cached_payload:
            self.set_access_token(cached_payload["access_token"], cached_payload["expires_at"])

    def refresh_token(self) -> SuccessResponse:
        """Refresh Kite token via Selenium automation and update in-memory and Redis cache.

        A headless Chrome instance is only ever needed for this login flow — every other
        KiteService method (quotes, margins, orders, GTTs) talks straight to the Kite API over
        the cached access token. Booting Selenium eagerly in __init__ meant every consumer,
        including a plain quote lookup, paid for a full Chrome process — and short-lived
        consumers that construct a fresh KiteService per call (e.g. the quote SSE stream, which
        does so once per connection) leaked one every time since nothing outside this method
        ever called close_driver(). Twenty such orphaned Chrome processes were found running in
        the backend container from exactly this pattern, starving new connections of resources
        and leaving the dashboard's live-quote stream unable to complete a single request.
        """
        self.selenium_service = SeleniumService()
        try:
            request_token = self._login_and_retrieve_token()
            access_token = self._generate_access_token(request_token)

            self.set_access_token(access_token)
            self._cache_token(access_token)

            logger.info("Kite token refreshed and cached successfully.")
            expires_at = self._token_expires_at.isoformat() if self._token_expires_at else None
            return SuccessResponse(success=True, message="TOKEN_REFRESHED", data={ "expires_at": expires_at })
        except Exception:
            logger.exception("Failed to refresh Kite token.")
            raise
        finally:
            self.selenium_service.close_driver()
            self.selenium_service = None

    def _login_and_retrieve_token(self) -> str:
        """Automate Kite Login and retrieve access token from the redirect URL."""
        try:
            login_url = self.kite.login_url()
            logger.info("Starting Kite Token Refresh")

            self.selenium_service.driver.get(login_url)
            self.selenium_service.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

            user_id_field = self.selenium_service.find_first_present([(By.ID, "userid")], "user_id_field")
            self.selenium_service.fill_input(user_id_field, settings.KITE_LOGIN_ID)

            password_field = self.selenium_service.find_first_present([(By.ID, "password")], "password_field")
            self.selenium_service.fill_input(password_field, settings.KITE_PASSWORD)

            login_button = self.selenium_service.find_first_clickable([(By.CSS_SELECTOR, "button[type='submit']")], "login_button")
            self.selenium_service.safe_click(login_button)

            totp_field = self.selenium_service.find_first_present([(By.CSS_SELECTOR, "input[type='number']")], "totp_field")
            totp_code = pyotp.TOTP(settings.KITE_TOTP_SECRET).now()
            self.selenium_service.fill_input(totp_field, totp_code)

            self.selenium_service.wait.until(lambda active_driver: 'request_token' in active_driver.current_url or 'error' in active_driver.current_url)
            current_url = self.selenium_service.driver.current_url

            parsed = urlparse(current_url)
            query_params = parse_qs(parsed.query)
            request_token = query_params.get("request_token", [None])[0]

            if not request_token:
                raise RuntimeError(f"Failed to retrieve request token. Current URL: {current_url}")

            logger.info("Kite login successful, retrieved request token.")
            return request_token
        except TimeoutException as e:
            logger.exception("Timeout while waiting for elements during Kite login.")
            raise RuntimeError("Timeout during Kite login process.") from e

    def ensure_valid_token(self, force_refresh: bool = False) -> SuccessResponse:
        """Ensure a token exists and refresh when forced or missing/expired."""
        with self._token_lock:
            is_missing = self.kite.access_token is None
            is_expired = self._token_expires_at is None or datetime.utcnow() >= self._token_expires_at

            if force_refresh or is_missing or is_expired:
                logger.info("Token refresh required. Force: {}, Missing: {}, Expired: {}", force_refresh, is_missing, is_expired)
                return self.refresh_token()

            token_expires_at = self._token_expires_at.isoformat() if self._token_expires_at else "None"

            # logger.debug(f"Token validation reused existing in-memory token with expiry {token_expires_at}")
            return SuccessResponse(success=True, message="VALID_TOKEN_EXISTS", data={ "expires_at": token_expires_at if token_expires_at != "None" else None })

    def set_access_token(self, access_token: str, expires_at: datetime | None = None) -> None:
        """Set a newly generated access token on the Kite client and cache expiry metadata."""
        self.kite.set_access_token(access_token)
        self._token_expires_at = expires_at or (datetime.utcnow() + timedelta(hours=24))

    def _generate_access_token(self, request_token: str) -> str:
        """Generate access token using request_token and api_secret"""
        logger.info("Generating access token using request token via API")
        data = self.kite.generate_session(request_token, api_secret=self.api_secret)
        access_token = data["access_token"]
        logger.info(f"Kite access token generated successfully. {access_token[:6]}****")
        return access_token

    def _build_redis_client(self) -> Redis | None:
        """Create Redis client for token cache; return None when Redis is not configured."""
        if not settings.REDIS_URL:
            logger.info("REDIS_URL not configured. Token cache will be in-memory only.")
            return None

        try:
            client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
            client.ping()
            logger.info("Connected to Redis for Kite token cache.")
            return client
        except Exception:
            logger.opt(exception=True).warning("Unable to connect to Redis. Token cache will be in-memory only.")
            return None

    def _get_cached_token(self) -> Dict[str, Any] | None:
        """Read token from Redis cache and validate payload shape."""
        if self._redis_client is None:
            return None

        try:
            raw_payload = self._redis_client.get(self.TOKEN_CACHE_KEY)
            if not raw_payload:
                return None

            payload = json.loads(raw_payload)
            access_token = payload.get("access_token")
            expires_at_raw = payload.get("expires_at")
            if not access_token or not expires_at_raw:
                return None

            expires_at = datetime.fromisoformat(expires_at_raw)
            if datetime.utcnow() >= expires_at:
                return None

            return { "access_token": access_token, "expires_at": expires_at }
        except (RedisError, ValueError, TypeError, json.JSONDecodeError):
            logger.opt(exception=True).warning("Unable to read Kite token from cache.")
            return None

    def _cache_token(self, access_token: str) -> None:
        if self._redis_client is None:
            logger.warning("Redis client not available, skipping token caching.")
            return

        try:
            expires_at = self._token_expires_at or (datetime.utcnow() + timedelta(hours=24))
            payload = { 'access_token': access_token, 'expires_at': expires_at.isoformat() }
            self._redis_client.set(self.TOKEN_CACHE_KEY, json.dumps(payload), ex=self.TOKEN_CACHE_TTL_SECONDS)
        except RedisError:
            logger.opt(exception=True).warning("Failed to cache token in Redis.")

    # Backoff between retries of a Kite call that failed on a transient connection error (DNS
    # resolution, connection refused/reset, read timeout) — not on a rejected/invalid request,
    # which would just fail again identically. One retry immediately, one after a short wait;
    # observed necessary when a live intraday quote batch hit a one-off DNS resolution failure
    # reaching api.kite.trade with no other retry path, dropping that entire 10-minute refresh
    # cycle even though the surrounding cycles succeeded fine.
    NETWORK_RETRY_DELAYS_SECONDS = [0, 2]

    def call_with_auto_refresh(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Run a Kite API call, retrying once after a token refresh on token-expired errors, and
        a couple more times (with a short backoff) on a transient connection failure."""
        self.ensure_valid_token()

        def _call_with_token_refresh() -> Any:
            try:
                return func(*args, **kwargs)
            except TokenException:
                logger.info("Kite token expired during API call. Refreshing token and retrying once.")
                self.ensure_valid_token(force_refresh=True)
                return func(*args, **kwargs)

        last_attempt = len(self.NETWORK_RETRY_DELAYS_SECONDS) - 1
        for attempt, delay in enumerate(self.NETWORK_RETRY_DELAYS_SECONDS):
            if delay:
                time.sleep(delay)
            try:
                return _call_with_token_refresh()
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as exc:
                if attempt == last_attempt:
                    raise
                logger.warning(f"Transient network error calling Kite API (attempt {attempt + 1}/{last_attempt + 1}): {exc}. Retrying.")

    # ---- Token Management Methods End ----

    # ---- Order Service ----

    def _order_request(self, method: str, path: str, **kwargs) -> Any:
        """Send a request to the order service, injecting the current access token."""
        if not settings.KITE_ORDER_SERVICE_URL:
            raise ExternalAPIError(api_name="OrderService", message="KITE_ORDER_SERVICE_URL is not configured.")

        self.ensure_valid_token()
        token = self.kite.access_token
        url = f"{settings.KITE_ORDER_SERVICE_URL.rstrip('/')}{path}"
        headers = { "Authorization": f"Bearer {token}"}

        try:
            response = httpx.request(method, url, headers=headers, timeout=30, **kwargs)
            response.raise_for_status()
            return response.json().get("data")
        except httpx.HTTPStatusError as exc:
            body = exc.response.text
            logger.error("Order service {} {} returned {}: {}", method, path, exc.response.status_code, body)
            raise ExternalAPIError(api_name="OrderService", message=f"Order service error {exc.response.status_code}: {body}")
        except httpx.RequestError as exc:
            logger.error("Order service request failed for {} {}: {}", method, path, exc)
            raise ExternalAPIError(api_name="OrderService", message=f"Order service unreachable: {exc}")

    # ---- Other Methods ----

    def fetch_instruments(self) -> pd.DataFrame:
        """Fetch all NSE EQ instruments and NSE INDICES from Kite API as a raw DataFrame.

        Universe filtering (e.g. NIFTY 500 cross-reference) is the caller's responsibility.
        """
        try:
            self.ensure_valid_token()

            logger.info("Fetching instruments from Kite API.")
            all_instruments = self.call_with_auto_refresh(self.kite.instruments)
            instruments_df = pd.DataFrame(all_instruments)
            logger.info(f"Fetched {len(instruments_df)} total instruments from Kite API.")

            nse_instruments = instruments_df[instruments_df['exchange'] == 'NSE']

            nse_eq = nse_instruments[nse_instruments['segment'] == 'NSE']
            nse_indices = nse_instruments[nse_instruments['segment'] == 'INDICES']

            combined = pd.concat([ nse_eq, nse_indices ])
            logger.info(f"Returning {len(nse_eq)} NSE EQ + {len(nse_indices)} INDICES instruments.")

            return combined
        except Exception:
            logger.exception("Error fetching instruments from Kite API.")
            raise ExternalAPIError(api_name="Kite", message="Failed to fetch instruments from Kite API.")

    def get_quotes(self, tickers: list[str]) -> dict:
        """Fetch the latest quote for the given tickers from Kite API."""
        try:
            self.ensure_valid_token()
            quote = self.call_with_auto_refresh(self.kite.quote, tickers)
            return quote
        except Exception as exc:
            logger.exception(f"Error fetching quote for tickers {tickers} from Kite API. Error {exc}")
            raise ExternalAPIError(api_name="Kite", message=f"Failed to fetch quote for tickers {tickers}.")

    def get_historical_data(self, instrument_token: int, from_date: datetime, to_date: datetime, interval: str) -> pd.DataFrame:
        """Fetch historical data for a given instrument from Kite API."""
        try:
            self.ensure_valid_token()
            historical_data = self.call_with_auto_refresh(self.kite.historical_data, instrument_token, from_date, to_date, interval)
            return pd.DataFrame(historical_data)
        except Exception as exc:
            logger.exception(f"Error fetching historical data for instrument {instrument_token} from {from_date} to {to_date} with interval {interval}. Error {exc}")
            raise ExternalAPIError(api_name="Kite", message=f"Failed to fetch historical data for instrument {instrument_token}.")

    def get_holdings(self) -> list[dict]:
        """Fetch the current holdings from Kite API, excluding configured tickers."""
        try:
            self.ensure_valid_token()
            holdings = self.call_with_auto_refresh(self.kite.holdings)
            return [ h for h in holdings if h.get("tradingsymbol") not in settings.HOLDINGS_EXCLUDE ]
        except Exception as exc:
            logger.exception(f"Error fetching holdings from Kite API. Error {exc}")
            raise ExternalAPIError(api_name="Kite", message="Failed to fetch holdings.")

    def get_margins(self) -> dict:
        """Fetch available funds/margins from Kite API."""
        try:
            self.ensure_valid_token()
            return self.call_with_auto_refresh(self.kite.margins)
        except Exception as exc:
            logger.exception(f"Error fetching margins from Kite API. Error {exc}")
            raise ExternalAPIError(api_name="Kite", message="Failed to fetch margins.")

    def get_basket_order_margins(self, orders: list[dict]) -> float:
        """Real SPAN+exposure margin required to hold a basket of orders together, with hedge
        benefit applied (e.g. a short strike's margin reduced by its protective long strike) —
        read-only estimation, never places anything. Returns final.total: the post-hedge-benefit
        combined margin, which is what actually needs to be free for the basket to fill. Each
        order dict needs exchange/tradingsymbol/transaction_type/variety/product/order_type/quantity."""
        try:
            self.ensure_valid_token()
            response = self.call_with_auto_refresh(self.kite.basket_order_margins, orders, True, "compact")
            return float(response["final"]["total"])
        except Exception as exc:
            logger.exception(f"Error fetching basket order margins from Kite API. Error {exc}")
            raise ExternalAPIError(api_name="Kite", message="Failed to fetch basket order margins.")

    def get_orders(self) -> list[dict]:
        """Fetch all orders placed today via the order service."""
        try:
            return self._order_request("GET", "/orders") or []
        except Exception as exc:
            logger.exception("Error fetching orders: {}", exc)
            raise

    def get_order(self, order_id: str) -> dict | None:
        """Fetch a single order's current status. Returns None if not found."""
        try:
            orders = self._order_request("GET", "/orders") or []
            for o in orders:
                if str(o.get("order_id")) == str(order_id):
                    return o
            return None
        except Exception as exc:
            logger.exception("Error fetching order {}: {}", order_id, exc)
            raise

    def cancel_order(self, variety: str, order_id: str) -> None:
        """Cancel an open order via the order service."""
        try:
            self._order_request("DELETE", f"/orders/{variety}/{order_id}")
            logger.info("Cancelled order {}", order_id)
        except Exception as exc:
            logger.exception("Error cancelling order {}: {}", order_id, exc)
            raise ExternalAPIError(api_name="OrderService", message=f"Failed to cancel order {order_id}.")

    def get_order_trades(self, order_id: str) -> list[dict]:
        """Fetch trades (fills) for a given order ID via the order service."""
        try:
            return self._order_request("GET", f"/orders/{order_id}/trades") or []
        except Exception as exc:
            logger.exception("Error fetching trades for order {}: {}", order_id, exc)
            raise

    def place_order(self, variety: str, exchange: str, tradingsymbol: str, transaction_type: str, quantity: int, product: str, order_type: str, price: float = None, trigger_price: float = None) -> str:
        """Place an order via the order service and return the order ID."""
        body = dict(exchange=exchange, tradingsymbol=tradingsymbol, transaction_type=transaction_type, quantity=quantity, product=product, order_type=order_type)
        if price is not None:
            body["price"] = price
        if trigger_price is not None:
            body["trigger_price"] = trigger_price

        try:
            response = httpx.request("POST", f"{settings.KITE_ORDER_SERVICE_URL.rstrip('/')}/orders/{variety}", headers={ "Authorization": f"Bearer {self.kite.access_token}"}, json=body, timeout=30)
        except httpx.RequestError as exc:
            logger.error("Order service unreachable while placing order for {}: {}", tradingsymbol, exc)
            raise ExternalAPIError(api_name="OrderService", message=f"Order service unreachable: {exc}")

        if not response.is_success:
            error_msg = response.json().get("error", response.text)
            logger.error("Order service returned {} for {}: {}", response.status_code, tradingsymbol, error_msg)
            raise ExternalAPIError(api_name="OrderService", message=f"Failed to place order for {tradingsymbol}: {error_msg}")

        order_id = response.json().get("order_id")
        logger.info("Placed {} {} order for {}, qty={}, order_id={}", transaction_type, order_type, tradingsymbol, quantity, order_id)
        return str(order_id)

    def get_gtts(self) -> list[dict]:
        """Fetch all GTT orders via the order service."""
        try:
            return self._order_request("GET", "/gtt") or []
        except Exception as exc:
            logger.exception("Error fetching GTTs: {}", exc)
            raise

    def get_gtt(self, trigger_id: int) -> dict:
        """Fetch a single GTT order by trigger ID via the order service."""
        try:
            return self._order_request("GET", f"/gtt/{trigger_id}")
        except Exception as exc:
            logger.exception("Error fetching GTT {}: {}", trigger_id, exc)
            raise

    def place_gtt(self, trigger_type: str, tradingsymbol: str, exchange: str, trigger_values: list[float], last_price: float, orders: list[dict]) -> str:
        """Place a GTT order via the order service and return the GTT ID."""
        body = dict(trigger_type=trigger_type, tradingsymbol=tradingsymbol, exchange=exchange, trigger_values=trigger_values, last_price=last_price, orders=orders)

        try:
            response = httpx.request("POST", f"{settings.KITE_ORDER_SERVICE_URL.rstrip('/')}/gtt", headers={ "Authorization": f"Bearer {self.kite.access_token}"}, json=body, timeout=30)
        except httpx.RequestError as exc:
            logger.error("Order service unreachable while placing GTT for {}: {}", tradingsymbol, exc)
            raise ExternalAPIError(api_name="OrderService", message=f"Order service unreachable: {exc}")

        if not response.is_success:
            error_msg = response.json().get("error", response.text)
            logger.error("Order service returned {} for GTT {}: {}", response.status_code, tradingsymbol, error_msg)
            raise ExternalAPIError(api_name="OrderService", message=f"Failed to place GTT for {tradingsymbol}: {error_msg}")

        trigger_id = response.json().get("trigger_id")
        if isinstance(trigger_id, dict):
            trigger_id = trigger_id.get("trigger_id")
        logger.info("Placed GTT for {}, trigger_id={}", tradingsymbol, trigger_id)
        return str(trigger_id)

    def modify_gtt(self, trigger_id: int, trigger_type: str, tradingsymbol: str, exchange: str, trigger_values: list[float], last_price: float, orders: list[dict]) -> str:
        """Modify an existing GTT order via the order service."""
        try:
            body = dict(trigger_type=trigger_type, tradingsymbol=tradingsymbol, exchange=exchange, trigger_values=trigger_values, last_price=last_price, orders=orders)
            result = self._order_request("PUT", f"/gtt/{trigger_id}", json=body)
            logger.info("Modified GTT {} for {}", trigger_id, tradingsymbol)
            return str(result)
        except Exception as exc:
            logger.exception("Error modifying GTT {} for {}: {}", trigger_id, tradingsymbol, exc)
            raise ExternalAPIError(api_name="OrderService", message=f"Failed to modify GTT {trigger_id}.")

    def delete_gtt(self, trigger_id: int) -> None:
        """Cancel an existing GTT order via the order service."""
        try:
            self._order_request("DELETE", f"/gtt/{trigger_id}")
            logger.info("Deleted GTT {}", trigger_id)
        except Exception as exc:
            logger.exception("Error deleting GTT {}: {}", trigger_id, exc)
            raise ExternalAPIError(api_name="OrderService", message=f"Failed to delete GTT {trigger_id}.")

    # --- Utility Methods ---

    def _to_security_row(self, instruments: pd.DataFrame) -> pd.DataFrame:
        """Convert raw instruments DataFrame to the format required for the securities table."""
        # Define the mapping of columns from instruments to securities table
        securities_df = pd.DataFrame()

        securities_df['ticker'] = instruments['tradingsymbol']
        securities_df['display_name'] = instruments['name']
        securities_df['exchange'] = instruments['exchange']
        securities_df['broker_token'] = instruments['instrument_token']
        securities_df['exchange_token'] = instruments['exchange_token']
        securities_df['tick_size'] = instruments['tick_size']
        securities_df['type'] = instruments['segment'].apply(lambda x: SecurityType.INDEX.value if x == 'INDICES' else SecurityType.EQUITY.value)
        securities_df['is_active'] = True

        return securities_df
