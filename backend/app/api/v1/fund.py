# backend/app/api/v1/fund.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.fund import FundService
from app.schemas.base import APIResponse
from app.schemas.fund import CashFlowCreate
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.post("/cashflow", response_model=APIResponse)
async def create_cash_flow(payload: CashFlowCreate, db: Session = Depends(get_db)):
    """Record a manual deposit or withdrawal."""
    try:
        flow = FundService(db).record_cash_flow(flow_type=payload.flow_type, amount=payload.amount, flow_date=payload.flow_date, note=payload.note)
        return APIResponse(success=True, message="Cash flow recorded", data={ "id": flow.id, "flow_type": flow.flow_type, "amount": float(flow.amount), "flow_date": flow.flow_date, "note": flow.note })
    except Exception as exc:
        logger.error("Error recording cash flow: {}", exc, exc_info=True)
        return APIResponse(success=False, message=str(exc))


@router.get("/cashflow", response_model=APIResponse)
async def list_cash_flows(db: Session = Depends(get_db)):
    """Return all recorded cash flows."""
    try:
        flows = FundService(db).get_cash_flows()
        data = [{ "id": f.id, "flow_type": f.flow_type, "amount": float(f.amount), "flow_date": f.flow_date, "note": f.note } for f in flows]
        return APIResponse(success=True, message="Cash flows retrieved", data=data)
    except Exception as exc:
        logger.error("Error fetching cash flows: {}", exc, exc_info=True)
        return APIResponse(success=False, message=str(exc))
