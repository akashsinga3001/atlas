"""Celery tasks for Kite token refresh (scheduled and on-demand)."""

from datetime import datetime, timezone
from time import monotonic, sleep
from uuid import uuid4

from celery_app import celery_app
from redis import Redis
from redis.exceptions import RedisError

from config import settings
from services.brokers.kite import KiteService
from utils.logger import logger

REFRESH_LOCK_KEY = 'kite:token_refresh:lock'
REFRESH_LOCK_TTL_SECONDS = 600


def _get_redis_client() -> Redis:
    """Create a Redis client used for task-level distributed locking."""
    return Redis.from_url(settings.REDIS_URL, decode_responses=True)


def _acquire_lock(redis_client: Redis, owner_token: str) -> bool:
    """Acquire a short-lived distributed lock for token refresh."""
    return bool(redis_client.set(REFRESH_LOCK_KEY, owner_token, nx=True, ex=REFRESH_LOCK_TTL_SECONDS))


def _release_lock(redis_client: Redis, owner_token: str) -> None:
    """Release lock only if the current owner matches this task instance."""
    release_script = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
	return redis.call('DEL', KEYS[1])
end
return 0
"""
    redis_client.eval(release_script, 1, REFRESH_LOCK_KEY, owner_token)


def _wait_for_inflight_refresh(redis_client: Redis, timeout_seconds: int = 45, poll_interval_seconds: float = 1.5) -> bool:
    """Wait for an in-flight refresh lock to clear and report whether it cleared in time."""
    deadline = monotonic() + timeout_seconds
    while monotonic() < deadline:
        if not redis_client.exists(REFRESH_LOCK_KEY):
            return True
        sleep(poll_interval_seconds)
    return False


def _run_refresh(trigger_source: str) -> dict:
    """Run token refresh once with lock protection for reliability."""
    redis_client = _get_redis_client()
    owner_token = str(uuid4())
    lock_acquired = False

    try:
        lock_acquired = _acquire_lock(redis_client, owner_token)
        if not lock_acquired:
            if trigger_source == 'on_demand':
                logger.info('On-demand refresh waiting for in-flight refresh to complete')
                if _wait_for_inflight_refresh(redis_client):
                    service = KiteService()
                    result = service.ensure_valid_token(force_refresh=False)
                    result['trigger_source'] = trigger_source
                    result['timestamp'] = datetime.now(timezone.utc).isoformat()
                    result['skipped'] = False
                    result['waited_for_inflight_refresh'] = True
                    return result

            logger.info('Kite token refresh skipped because another refresh is in progress')
            return {'success': True, 'skipped': True, 'reason': 'refresh_in_progress', 'trigger_source': trigger_source, 'timestamp': datetime.now(timezone.utc).isoformat()}

        service = KiteService()
        result = service.refresh_token()
        result['trigger_source'] = trigger_source
        result['timestamp'] = datetime.now(timezone.utc).isoformat()
        result['skipped'] = False
        return result
    except RedisError as exc:
        logger.exception(f'Redis failure during lock handling: {exc}')
        raise
    finally:
        if lock_acquired:
            try:
                _release_lock(redis_client, owner_token)
            except RedisError:
                logger.warning('Failed to release kite token refresh lock; it will expire automatically')


@celery_app.task(name='jobs.refresh_token.kite_daily_refresh', bind=True, autoretry_for=(Exception, ), retry_backoff=True, retry_backoff_max=300, retry_jitter=True, retry_kwargs={'max_retries': 3})
def kite_daily_refresh(self) -> dict:
    """Run scheduled Kite token refresh at fixed daily time."""
    logger.info('Starting scheduled Kite token refresh task')
    return _run_refresh(trigger_source='scheduled')


@celery_app.task(name='jobs.refresh_token.kite_on_demand_refresh', bind=True, autoretry_for=(Exception, ), retry_backoff=True, retry_backoff_max=120, retry_jitter=True, retry_kwargs={'max_retries': 2})
def kite_on_demand_refresh(self, reason: str = 'token_expired') -> dict:
    """Run on-demand Kite token refresh when broker reports expiry errors."""
    logger.info(f'Starting on-demand Kite token refresh task. Reason: {reason}')
    result = _run_refresh(trigger_source='on_demand')
    result['reason'] = reason
    return result
