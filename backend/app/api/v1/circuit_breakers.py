# backend/app/api/v1/circuit_breakers.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.services.circuit_breaker import CircuitBreakerService
from app.schemas.base import APIResponse
from app.schemas.circuit_breaker import UpdateCircuitBreakerRequest
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("", response_model=APIResponse)
async def list_breakers(db: Session = Depends(get_db)) -> APIResponse:
    """Return all circuit breakers."""
    try:
        data = CircuitBreakerService(db).list_breakers()
        return APIResponse(success=True, message="Circuit breakers retrieved successfully.", data=data)
    except Exception as exc:
        logger.error(f"Failed to retrieve circuit breakers. Error: {str(exc)}", exc_info=True)
        return APIResponse(success=False, message="Failed to retrieve circuit breakers.", errors={ "detail": str(exc) })


@router.patch("/{breaker_id}", response_model=APIResponse)
async def update_breaker(breaker_id: int, request: UpdateCircuitBreakerRequest, db: Session = Depends(get_db)) -> APIResponse:
    """Toggle a circuit breaker on/off and/or edit its tunable params."""
    try:
        data = CircuitBreakerService(db).update_breaker(breaker_id, request)
        return APIResponse(success=True, message="Circuit breaker updated.", data=data)
    except NotFoundError as exc:
        return APIResponse(success=False, message=exc.message, errors=exc.details)
    except Exception as exc:
        logger.error(f"Failed to update circuit breaker {breaker_id}. Error: {str(exc)}", exc_info=True)
        return APIResponse(success=False, message="Failed to update circuit breaker.", errors={ "detail": str(exc) })
