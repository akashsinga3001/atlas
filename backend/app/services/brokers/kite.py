# backend/app/services/brokers/kite.py

import json
from datetime import datetime, timedelta
from threading import Lock
from typing import Any, Callable, Dict
from urllib.parse import parse_qs, urlparse
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

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
        self.selenium_service = SeleniumService()

        cached_payload = self._get_cached_token()
        if cached_payload:
            self.set_access_token(cached_payload["access_token"], cached_payload["expires_at"])

    def refresh_token(self) -> SuccessResponse:
        """Refresh Kite token via Selenium automation and update in-memory and Redis cache."""
        try:
            request_token = self._login_and_retrieve_token()
            access_token = self._generate_access_token(request_token)

            self.set_access_token(access_token)
            self._cache_token(access_token)

            logger.info("Kite token refreshed and cached successfully.")
            expires_at = self._token_expires_at.isoformat() if self._token_expires_at else None
            return SuccessResponse(success=True, message="TOKEN_REFRESHED", data={ "expires_at": expires_at })
        except Exception:
            logger.error("Failed to refresh Kite token.", exc_info=True)
            raise
        finally:
            self.selenium_service.close_driver()

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
            logger.error("Timeout while waiting for elements during Kite login.", exc_info=True)
            raise RuntimeError("Timeout during Kite login process.") from e

    def ensure_valid_token(self, force_refresh: bool = False) -> SuccessResponse:
        """Ensure a token exists and refresh when forced or missing/expired."""
        with self._token_lock:
            is_missing = self.kite.access_token is None
            is_expired = self._token_expires_at is None or datetime.utcnow() >= self._token_expires_at

            if force_refresh or is_missing or is_expired:
                logger.info("Token refresh required. Force: %s, Missing: %s, Expired: %s", force_refresh, is_missing, is_expired)
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
            logger.warning("Unable to connect to Redis. Token cache will be in-memory only.", exc_info=True)
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
            logger.warning("Unable to read Kite token from cache.", exc_info=True)
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
            logger.warning("Failed to cache token in Redis.", exc_info=True)

    def call_with_auto_refresh(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Run a Kite API call and retry once after token refresh on token-expired errors."""
        self.ensure_valid_token()

        try:
            return func(*args, **kwargs)
        except TokenException:
            logger.info("Kite token expired during API call. Refreshing token and retrying once.")
            self.ensure_valid_token(force_refresh=True)
            return func(*args, **kwargs)

    # ---- Token Management Methods End ----

    # ---- Other Methods ----

    def fetch_instruments(self) -> pd.DataFrame:
        """Fetch instruments from Kite API and return as a pandas DataFrame."""
        try:
            self.ensure_valid_token()

            # Step 1: Fetch instruments from Kite API
            logger.info("Fetching instruments from Kite API.")
            all_instruments = self.call_with_auto_refresh(self.kite.instruments)
            instruments_df = pd.DataFrame(all_instruments)
            logger.info(f"Fetched {len(instruments_df)} instruments from Kite API.")

            # Step 2: Filter for NSE instruments and log count
            logger.info("Filtering for NSE instruments.")
            nse_instruments = instruments_df[(instruments_df['exchange'] == 'NSE')]
            logger.info(f"Filtered {len(nse_instruments)} NSE instruments.")

            # Step 2: Filter for NFO-FUT instruments
            logger.info("Filtering for NFO-FUT instruments.")
            nfo_instruments = instruments_df[(instruments_df['segment'] == 'NFO-FUT')]
            logger.info(f"Filtered {len(nfo_instruments)} NFO-FUT instruments.")

            # Step 3: Identify unique underlying tickers and log count
            logger.info("Identifying unique underlying tickers.")
            unique_tickers = nfo_instruments['name'].nunique()
            logger.info(f"Identified {unique_tickers} unique underlying tickers.")

            # Step 4: Find underlying instruments based on unique tickers and log count
            logger.info("Finding underlying instruments based on unique tickers.")
            underlying_instruments = nse_instruments[nse_instruments['tradingsymbol'].isin(nfo_instruments['name'])]
            logger.info(f"Found {len(underlying_instruments)} underlying instruments based on unique tickers.")

            # Step 5: Find NSE INDICES instruments and log count
            logger.info("Finding NSE INDICES instruments.")
            nse_indices_instruments = nse_instruments[(nse_instruments['exchange'] == 'NSE') & (nse_instruments['segment'] == 'INDICES')]
            logger.info(f"Found {len(nse_indices_instruments)} NSE INDICES instruments.")

            # Step 6: Combine underlying instruments and NSE INDICES instruments, then log count
            logger.info("Combining underlying instruments and NSE INDICES instruments.")
            combined_instruments = pd.concat([ underlying_instruments, nse_indices_instruments ])
            logger.info(f"Combined instruments count: {len(combined_instruments)}")

            # Step 7: Convert combined instruments to the format required for the securities table
            logger.info("Converting combined instruments to the format required for the securities table.")
            final_df = self._to_security_row(combined_instruments)
            logger.info(f"Converted instruments to securities table format. Final count: {len(final_df)}")

            return final_df
        except Exception:
            logger.error("Error fetching instruments from Kite API.", exc_info=True)
            raise ExternalAPIError(api_name="Kite", message="Failed to fetch instruments from Kite API.")

    def get_quotes(self, tickers: list[str]) -> dict:
        """Fetch the latest quote for the given tickers from Kite API."""
        try:
            self.ensure_valid_token()
            quote = self.call_with_auto_refresh(self.kite.quote, tickers)
            return quote
        except Exception as exc:
            logger.error(f"Error fetching quote for tickers {tickers} from Kite API. Error {exc}", exc_info=True)
            raise ExternalAPIError(api_name="Kite", message=f"Failed to fetch quote for tickers {tickers}.")

    def get_historical_data(self, instrument_token: int, from_date: datetime, to_date: datetime, interval: str) -> pd.DataFrame:
        """Fetch historical data for a given instrument from Kite API."""
        try:
            self.ensure_valid_token()
            historical_data = self.call_with_auto_refresh(self.kite.historical_data, instrument_token, from_date, to_date, interval)
            return pd.DataFrame(historical_data)
        except Exception as exc:
            logger.error(f"Error fetching historical data for instrument {instrument_token} from {from_date} to {to_date} with interval {interval}. Error {exc}", exc_info=True)
            raise ExternalAPIError(api_name="Kite", message=f"Failed to fetch historical data for instrument {instrument_token}.")

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
        securities_df['lot_size'] = instruments['lot_size']
        securities_df['tick_size'] = instruments['tick_size']
        securities_df['type'] = instruments['segment'].apply(lambda x: SecurityType.INDEX.value if x == 'INDICES' else SecurityType.EQUITY.value)
        securities_df['expiry_date'] = instruments['expiry'].replace('', None)
        securities_df['is_active'] = True

        return securities_df
