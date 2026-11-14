from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import require_role
from app.models.user import User
from app.schemas.lot import BatchLotOut
from app.schemas.user import FarmerOut
from app.services import fpo_service
from app.services.fpo_member_service import FpoMemberService, get_fpo_member_service

router = APIRouter()          # mounted at /api/v1/pools (lot pooling)
farmers_router = APIRouter()  # mounted at /api/v1/fpo   (membership, Member 1)


@farmers_router.get("/farmers", response_model=list[FarmerOut])
async def list_fpo_farmers(
    user: User = Depends(require_role("FPO_ADMIN")),
    service: FpoMemberService = Depends(get_fpo_member_service),
):
    """List all farmers registered under the calling FPO admin's FPO."""
    return await service.list_farmers_for_admin(user)


class AggregateRequest(BaseModel):
    lot_ids: list[int] = Field(..., min_length=1)


@router.post("/aggregate", response_model=BatchLotOut, status_code=status.HTTP_201_CREATED)
async def aggregate_lots(
    payload: AggregateRequest,
    user: User = Depends(require_role("FPO_ADMIN")),
    db: AsyncSession = Depends(get_db),
):
    """Aggregate multiple lots into a single batch lot. FPO admin only."""
    return await fpo_service.aggregate_lots(db, user, payload.lot_ids)
