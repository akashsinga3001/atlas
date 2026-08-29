# backend/app/services/circuit_breaker.py

from sqlalchemy.orm import Session

from app.models.circuit_breaker import CircuitBreaker
from app.repositories.circuit_breaker import CircuitBreakerRepository
from app.schemas.circuit_breaker import CircuitBreakerResponse, UpdateCircuitBreakerRequest
from app.core.exceptions import NotFoundError
from app.utils.logger import get_logger

logger = get_logger(__name__)


class CircuitBreakerService:
    """Service for reading and configuring automatic risk-control circuit breakers."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = CircuitBreakerRepository(db)

    def list_breakers(self) -> list[dict]:
        """Return all circuit breakers."""
        return [self._build_response(b) for b in self.repo.get_all_breakers()]

    def _build_response(self, breaker: CircuitBreaker) -> dict:
        """Serialise a circuit breaker to a dict."""
        return CircuitBreakerResponse(
            id=breaker.id, type=breaker.type, enabled=breaker.enabled, params=breaker.params or {},
            last_triggered_at=breaker.last_triggered_at, last_reason=breaker.last_reason, updated_at=breaker.updated_at,
        ).model_dump()

    def update_breaker(self, breaker_id: int, data: UpdateCircuitBreakerRequest) -> dict:
        """Toggle a circuit breaker on/off and/or edit its tunable params."""
        breaker = self.repo.get_by_id(breaker_id)
        if not breaker:
            raise NotFoundError(resource="CircuitBreaker", identifier=str(breaker_id))

        updates = data.model_dump(exclude_none=True)
        breaker = self.repo.update(breaker, updates)
        return self._build_response(breaker)

    def acknowledge_breaker(self, breaker_id: int) -> dict:
        """Clear a breaker's last trigger, dismissing it from the dashboard's attention feed.

        A breach never auto-clears on its own — reviewing and dismissing it is a deliberate
        human act, distinct from the kill switch itself (which independently gates new entries).
        Acknowledging does not re-enable trading; it only stops a resolved, historical breach
        from permanently reading as a live one.
        """
        breaker = self.repo.get_by_id(breaker_id)
        if not breaker:
            raise NotFoundError(resource="CircuitBreaker", identifier=str(breaker_id))

        breaker = self.repo.update(breaker, {"last_triggered_at": None, "last_reason": None})
        return self._build_response(breaker)
