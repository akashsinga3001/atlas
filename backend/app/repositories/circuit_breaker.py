# backend/app/repositories/circuit_breaker.py

from typing import Optional
from sqlalchemy.orm import Session

from app.models.circuit_breaker import CircuitBreaker
from app.repositories.base import BaseRepository


class CircuitBreakerRepository(BaseRepository[CircuitBreaker]):
    """Repository class for managing CircuitBreaker data in the database."""

    def __init__(self, db: Session):
        super().__init__(CircuitBreaker, db)

    def get_all_breakers(self) -> list[CircuitBreaker]:
        """Fetch all circuit breakers, ordered by type."""
        return self.db_session.query(CircuitBreaker).order_by(CircuitBreaker.type.asc()).all()

    def get_by_type(self, type: str) -> Optional[CircuitBreaker]:
        """Fetch a circuit breaker by its unique type."""
        return self.db_session.query(CircuitBreaker).filter(CircuitBreaker.type == type).first()
