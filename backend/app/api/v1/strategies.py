# backend/app/api/v1/strategies.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import AtlasException, InternalError
from app.services.strategy import StrategyService
from app.schemas.base import APIResponse
from app.schemas.strategy import CreateStrategyVersionRequest, SetStrategyActiveRequest
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("", response_model=APIResponse)
async def list_strategies(db: Session = Depends(get_db)) -> APIResponse:
    """Return all strategies with their active version, config schema fields, and version count."""
    try:
        data = StrategyService(db).list_strategies()
        return APIResponse(success=True, message="Strategies retrieved successfully.", data=data)
    except AtlasException:
        raise
    except Exception as exc:
        logger.exception(f"Failed to retrieve strategies. Error: {str(exc)}")
        raise InternalError(message="Failed to retrieve strategies.", details={ "detail": str(exc) }) from exc


@router.patch("/{strategy_id}", response_model=APIResponse)
async def set_active(strategy_id: int, request: SetStrategyActiveRequest, db: Session = Depends(get_db)) -> APIResponse:
    """Enable or disable a strategy — disabled strategies skip new signal generation and new entries only; exits are unaffected."""
    try:
        data = StrategyService(db).set_active(strategy_id, request.is_active)
        return APIResponse(success=True, message=f"Strategy {'enabled' if request.is_active else 'disabled'}.", data=data)
    except AtlasException:
        raise
    except Exception as exc:
        logger.exception(f"Failed to set active state for strategy {strategy_id}. Error: {str(exc)}")
        raise InternalError(message="Failed to update strategy.", details={ "detail": str(exc) }) from exc


@router.get("/{strategy_id}/versions", response_model=APIResponse)
async def get_version_history(strategy_id: int, db: Session = Depends(get_db)) -> APIResponse:
    """Return the full version history for a strategy, newest first."""
    try:
        data = StrategyService(db).get_version_history(strategy_id)
        return APIResponse(success=True, message="Version history retrieved successfully.", data=data)
    except AtlasException:
        raise
    except Exception as exc:
        logger.exception(f"Failed to retrieve version history for strategy {strategy_id}. Error: {str(exc)}")
        raise InternalError(message="Failed to retrieve version history.", details={ "detail": str(exc) }) from exc


@router.get("/{strategy_id}/runs", response_model=APIResponse)
async def get_run_history(strategy_id: int, db: Session = Depends(get_db)) -> APIResponse:
    """Return the most recent strategy runs across every version, newest first."""
    try:
        data = StrategyService(db).get_run_history(strategy_id)
        return APIResponse(success=True, message="Run history retrieved successfully.", data=data)
    except AtlasException:
        raise
    except Exception as exc:
        logger.exception(f"Failed to retrieve run history for strategy {strategy_id}. Error: {str(exc)}")
        raise InternalError(message="Failed to retrieve run history.", details={ "detail": str(exc) }) from exc


@router.post("/{strategy_id}/versions", response_model=APIResponse)
async def create_version(strategy_id: int, request: CreateStrategyVersionRequest, db: Session = Depends(get_db)) -> APIResponse:
    """Validate and insert a new, inactive config version for a strategy."""
    try:
        data = StrategyService(db).create_version(strategy_id, request.config)
        return APIResponse(success=True, message="New strategy version created.", data=data)
    except AtlasException:
        raise
    except Exception as exc:
        logger.exception(f"Failed to create version for strategy {strategy_id}. Error: {str(exc)}")
        raise InternalError(message="Failed to create strategy version.", details={ "detail": str(exc) }) from exc


@router.post("/{strategy_id}/versions/{version_id}/activate", response_model=APIResponse)
async def activate_version(strategy_id: int, version_id: int, db: Session = Depends(get_db)) -> APIResponse:
    """Activate a strategy version, atomically deactivating all other versions of the same strategy."""
    try:
        data = StrategyService(db).activate_version(strategy_id, version_id)
        return APIResponse(success=True, message="Strategy version activated.", data=data)
    except AtlasException:
        raise
    except Exception as exc:
        logger.exception(f"Failed to activate version {version_id} for strategy {strategy_id}. Error: {str(exc)}")
        raise InternalError(message="Failed to activate strategy version.", details={ "detail": str(exc) }) from exc
