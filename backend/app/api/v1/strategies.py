# backend/app/api/v1/strategies.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import NotFoundError, ValidationError
from app.services.strategy import StrategyService
from app.schemas.base import APIResponse
from app.schemas.strategy import CreateStrategyVersionRequest
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("", response_model=APIResponse)
async def list_strategies(db: Session = Depends(get_db)) -> APIResponse:
    """Return all strategies with their active version, config schema fields, and version count."""
    try:
        data = StrategyService(db).list_strategies()
        return APIResponse(success=True, message="Strategies retrieved successfully.", data=data)
    except Exception as exc:
        logger.error(f"Failed to retrieve strategies. Error: {str(exc)}", exc_info=True)
        return APIResponse(success=False, message="Failed to retrieve strategies.", errors={ "detail": str(exc) })


@router.get("/{strategy_id}/versions", response_model=APIResponse)
async def get_version_history(strategy_id: int, db: Session = Depends(get_db)) -> APIResponse:
    """Return the full version history for a strategy, newest first."""
    try:
        data = StrategyService(db).get_version_history(strategy_id)
        return APIResponse(success=True, message="Version history retrieved successfully.", data=data)
    except NotFoundError as exc:
        return APIResponse(success=False, message=exc.message, errors=exc.details)
    except Exception as exc:
        logger.error(f"Failed to retrieve version history for strategy {strategy_id}. Error: {str(exc)}", exc_info=True)
        return APIResponse(success=False, message="Failed to retrieve version history.", errors={ "detail": str(exc) })


@router.post("/{strategy_id}/versions", response_model=APIResponse)
async def create_version(strategy_id: int, request: CreateStrategyVersionRequest, db: Session = Depends(get_db)) -> APIResponse:
    """Validate and insert a new, inactive config version for a strategy."""
    try:
        data = StrategyService(db).create_version(strategy_id, request.config)
        return APIResponse(success=True, message="New strategy version created.", data=data)
    except (NotFoundError, ValidationError) as exc:
        return APIResponse(success=False, message=exc.message, errors=exc.details)
    except Exception as exc:
        logger.error(f"Failed to create version for strategy {strategy_id}. Error: {str(exc)}", exc_info=True)
        return APIResponse(success=False, message="Failed to create strategy version.", errors={ "detail": str(exc) })


@router.post("/{strategy_id}/versions/{version_id}/activate", response_model=APIResponse)
async def activate_version(strategy_id: int, version_id: int, db: Session = Depends(get_db)) -> APIResponse:
    """Activate a strategy version, atomically deactivating all other versions of the same strategy."""
    try:
        data = StrategyService(db).activate_version(strategy_id, version_id)
        return APIResponse(success=True, message="Strategy version activated.", data=data)
    except NotFoundError as exc:
        return APIResponse(success=False, message=exc.message, errors=exc.details)
    except Exception as exc:
        logger.error(f"Failed to activate version {version_id} for strategy {strategy_id}. Error: {str(exc)}", exc_info=True)
        return APIResponse(success=False, message="Failed to activate strategy version.", errors={ "detail": str(exc) })
