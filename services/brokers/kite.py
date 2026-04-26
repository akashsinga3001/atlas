"""
Kite Connect API integration for the Atlas application. This module provides functions to interact with the Kite Connect API, including authentication, fetching market data, and placing orders.
"""

import json
from datetime import date, datetime, timedelta
from threading import Lock
from typing import Any, Callable, Dict
from urllib.parse import parse_qs, urlparse

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import ElementClickInterceptedException, StaleElementReferenceException, TimeoutException
from kiteconnect import KiteConnect
from redis import Redis
from redis.exceptions import RedisError

import pyotp

from config import settings
from utils.logger import logger


class KiteService:
    """Service class for interacting with the Kite Connect API."""

    TOKEN_CACHE_KEY = 'kite:access_token'
    TOKEN_CACHE_TTL_SECONDS = 24 * 60 * 60
    TOKEN_EXPIRED_MARKERS = ('token is invalid', 'invalid token', 'token expired', 'session expired', 'authorization token is invalid')

    def __init__(self):
        self.api_key = settings.KITE_API_KEY
        self.api_secret = settings.KITE_API_SECRET
        self.kite = KiteConnect(api_key=self.api_key)
        self._token_expires_at: datetime | None = None
        self._token_lock = Lock()
        self._redis_client = self._build_redis_client()

        cached_payload = self._load_cached_token()
        if cached_payload:
            self.set_access_token(cached_payload['access_token'], cached_payload['expires_at'])

    def refresh_token(self) -> Dict[str, Any]:
        """Refresh Kite token via Selenium login and update the in-memory/API client token."""
        driver = None

        try:
            logger.info('=' * 80)
            logger.info('STARTING KITE TOKEN REFRESH')
            logger.info('=' * 80)

            driver = self._setup_driver()
            request_token = self._login_and_retrieve_token(driver)
            access_token = self._generate_access_token(request_token)

            self.set_access_token(access_token)
            self._cache_token(access_token)

            logger.info('=' * 80)
            logger.info('KITE TOKEN REFRESH SUCCESS')
            logger.info('Token updated on active Kite client')
            logger.info('=' * 80)

            expires_at = self._token_expires_at.isoformat() if self._token_expires_at else None
            return {'success': True, 'expires_at': expires_at, 'token_prefix': f'{access_token[:6]}***'}
        except Exception as exc:
            logger.exception(f'Kite token refresh failed: {exc}')
            raise
        finally:
            if driver:
                driver.quit()
                logger.info('Browser closed')

    def ensure_valid_token(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Ensure a token exists and refresh when forced or missing/expired."""
        with self._token_lock:
            is_missing = self.kite.access_token is None
            is_expired = self._token_expires_at is None or datetime.utcnow() >= self._token_expires_at

            if force_refresh or is_missing or is_expired:
                return self.refresh_token()

            return {'success': True, 'refreshed': False, 'expires_at': self._token_expires_at.isoformat() if self._token_expires_at else None}

    def execute_with_auto_refresh(self, operation: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute a Kite operation and refresh token once if the first attempt fails due to token expiry."""
        self.ensure_valid_token()

        try:
            return operation(*args, **kwargs)
        except Exception as exc:
            if not self._is_token_expired_error(exc):
                raise

            logger.warning('Detected token-expired error from broker operation, refreshing and retrying once')
            self.ensure_valid_token(force_refresh=True)
            return operation(*args, **kwargs)

    def fetch_instruments(self, segment: str | None = None) -> list[Dict[str, Any]]:
        """Fetch Kite instruments and optionally filter them by segment."""
        instruments = self.execute_with_auto_refresh(self.kite.instruments)

        if segment is None:
            return instruments

        expected_segment = segment.upper()
        return [item for item in instruments if str(item.get('segment', '')).upper() == expected_segment]

    def fetch_historical_candles(self, instrument_token: str, from_date: date, to_date: date, interval: str = 'day', continuous: bool = False) -> list[Dict[str, Any]]:
        """Fetch historical candle data from Kite and normalize to a stable shape."""
        raw_candles = self.execute_with_auto_refresh(self.kite.historical_data, instrument_token=int(instrument_token), from_date=from_date, to_date=to_date, interval=interval, continuous=continuous, oi=False)

        normalized: list[Dict[str, Any]] = []
        for row in raw_candles:
            candle_timestamp = row.get('date')
            if candle_timestamp is None:
                continue

            candle_date = candle_timestamp.date() if isinstance(candle_timestamp, datetime) else candle_timestamp
            normalized.append({'candle_date': candle_date, 'open': row.get('open'), 'high': row.get('high'), 'low': row.get('low'), 'close': row.get('close'), 'volume': row.get('volume', 0)})

        return normalized

    def get_access_token(self) -> str | None:
        """Return the current access token from the Kite client."""
        return self.kite.access_token

    def set_access_token(self, access_token: str, expires_at: datetime | None = None) -> None:
        """Set a newly generated access token on the Kite client and cache expiry metadata."""
        self.kite.set_access_token(access_token)
        self._token_expires_at = expires_at or (datetime.utcnow() + timedelta(hours=24))

    def _setup_driver(self) -> webdriver.Chrome:
        """Setup headless Chrome WebDriver with auto-detected browser/driver."""
        chrome_options = Options()
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')

        driver = webdriver.Chrome(options=chrome_options)
        logger.info('Headless Chrome WebDriver initialized')
        return driver

    def _login_and_retrieve_token(self, driver: webdriver.Chrome) -> str:
        """Automate Kite login and extract request_token from callback URL."""
        try:
            login_url = self.kite.login_url()
            logger.info('Navigating to Kite login URL')

            driver.get(login_url)
            wait = WebDriverWait(driver, 30)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, 'body')))

            user_id_field = self._find_first_present(driver, [
                (By.ID, 'userid'),
                (By.NAME, 'user_id'),
                (By.CSS_SELECTOR, "input[type='text'][autocomplete='username']"),
                (By.CSS_SELECTOR, "input[id*='user']"),
            ], 'user id input')
            self._fill_input(user_id_field, settings.KITE_USER_ID)

            password_field = self._find_first_present(driver, [
                (By.ID, 'password'),
                (By.NAME, 'password'),
                (By.CSS_SELECTOR, "input[type='password']"),
            ], 'password input')
            self._fill_input(password_field, settings.KITE_PASSWORD)

            login_button = self._find_first_clickable(driver, [
                (By.CSS_SELECTOR, "button[type='submit']"),
                (By.CSS_SELECTOR, "button.button-orange"),
                (By.XPATH, "//button[contains(., 'Login') or contains(., 'Continue')]"),
            ], 'login button')
            login_button.click()

            totp_field = self._find_first_present(driver, [
                (By.CSS_SELECTOR, "input[type='number']"),
                (By.NAME, 'otp'),
                (By.CSS_SELECTOR, "input[autocomplete='one-time-code']"),
                (By.CSS_SELECTOR, "input[type='tel']"),
            ], 'TOTP input')
            totp_code = self._generate_totp()
            logger.info(f'Generated TOTP: {totp_code[:2]}****')
            self._fill_input(totp_field, totp_code)

            if not self._wait_for_callback_url(driver, timeout_seconds=5):
                submit_button = self._find_first_clickable(driver, [
                    (By.CSS_SELECTOR, "button[type='submit']"),
                    (By.XPATH, "//button[contains(., 'Continue') or contains(., 'Submit') or contains(., 'Verify')]"),
                ], 'TOTP submit button')
                self._safe_click(driver, submit_button)

            wait.until(lambda active_driver: 'request_token' in active_driver.current_url or 'error' in active_driver.current_url)
            current_url = driver.current_url

            parsed = urlparse(current_url)
            query_params = parse_qs(parsed.query)
            request_token = query_params.get('request_token', [None])[0]

            if not request_token:
                raise RuntimeError(f'Kite login failed: request_token missing in callback URL: {current_url[:120]}')

            logger.info('Kite request token extracted successfully')
            return request_token
        except TimeoutException as exc:
            logger.error(f'Timeout during Kite login: {exc}')
            raise RuntimeError('Kite login timeout. Verify credentials or Kite website status.') from exc

    def _find_first_present(self, driver: webdriver.Chrome, locators: list[tuple[str, str]], element_name: str, timeout_seconds: int = 6):
        """Return the first present element from a list of locator candidates."""
        for locator in locators:
            try:
                return WebDriverWait(driver, timeout_seconds).until(EC.presence_of_element_located(locator))
            except TimeoutException:
                continue

        raise RuntimeError(f'Unable to locate {element_name} on Kite login page')

    def _find_first_clickable(self, driver: webdriver.Chrome, locators: list[tuple[str, str]], element_name: str, timeout_seconds: int = 6):
        """Return the first clickable element from a list of locator candidates."""
        for locator in locators:
            for _ in range(2):
                try:
                    return WebDriverWait(driver, timeout_seconds).until(EC.element_to_be_clickable(locator))
                except (TimeoutException, StaleElementReferenceException):
                    continue

        raise RuntimeError(f'Unable to locate clickable {element_name} on Kite login page')

    def _safe_click(self, driver: webdriver.Chrome, element) -> None:
        """Click element with JS fallback when regular click is blocked by transient DOM state."""
        try:
            element.click()
        except (ElementClickInterceptedException, StaleElementReferenceException):
            driver.execute_script('arguments[0].click();', element)

    def _wait_for_callback_url(self, driver: webdriver.Chrome, timeout_seconds: int) -> bool:
        """Return True when callback URL contains either request_token or error."""
        try:
            WebDriverWait(driver, timeout_seconds).until(lambda active_driver: 'request_token' in active_driver.current_url or 'error' in active_driver.current_url)
            return True
        except TimeoutException:
            return False

    def _fill_input(self, element, value: str) -> None:
        """Clear and fill an input field safely."""
        element.clear()
        element.send_keys(value)

    def _generate_totp(self) -> str:
        """Generate TOTP code from configured Kite secret."""
        totp = pyotp.TOTP(settings.KITE_TOTP_SECRET)
        return totp.now()

    def _generate_access_token(self, request_token: str) -> str:
        """Generate Kite access token using request token and API secret."""
        logger.info('Generating Kite access token via API')
        data = self.kite.generate_session(request_token, api_secret=self.api_secret)
        access_token = data['access_token']
        logger.info(f'Kite access token generated: {access_token[:6]}***')
        return access_token

    def _is_token_expired_error(self, error: Exception) -> bool:
        """Best-effort detection for token-expired broker errors."""
        message = str(error).lower()
        return any(marker in message for marker in self.TOKEN_EXPIRED_MARKERS)

    def _build_redis_client(self) -> Redis | None:
        """Build a Redis client for short-lived token sharing across processes."""
        try:
            return Redis.from_url(settings.REDIS_URL, decode_responses=True)
        except Exception as exc:
            logger.warning(f'Redis initialization failed, token cache disabled: {exc}')
            return None

    def _cache_token(self, access_token: str) -> None:
        """Cache access token in Redis for process-to-process reuse."""
        if self._redis_client is None:
            return

        try:
            expires_at = self._token_expires_at or (datetime.utcnow() + timedelta(hours=24))
            payload = {
                'access_token': access_token,
                'expires_at': expires_at.isoformat(),
            }
            self._redis_client.set(self.TOKEN_CACHE_KEY, json.dumps(payload), ex=self.TOKEN_CACHE_TTL_SECONDS)
        except RedisError as exc:
            logger.warning(f'Failed to cache Kite token in Redis: {exc}')

    def _load_cached_token(self) -> Dict[str, Any] | None:
        """Load previously refreshed token from Redis if available."""
        if self._redis_client is None:
            return None

        try:
            raw_payload = self._redis_client.get(self.TOKEN_CACHE_KEY)
            if not raw_payload:
                return None

            parsed_payload = json.loads(raw_payload)
            access_token = parsed_payload.get('access_token')
            expires_at_value = parsed_payload.get('expires_at')
            if not access_token or not expires_at_value:
                return None

            expires_at = datetime.fromisoformat(expires_at_value)
            if datetime.utcnow() >= expires_at:
                return None

            return {
                'access_token': access_token,
                'expires_at': expires_at,
            }
        except RedisError as exc:
            logger.warning(f'Failed to load Kite token from Redis cache: {exc}')
            return None
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            logger.warning(f'Invalid Kite token cache payload, ignoring cached token: {exc}')
            return None
