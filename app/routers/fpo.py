from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from app.dependencies.auth import require_role
from app.models.user import User
from app.dependencies.lots import get_lot_pool_service
from app.schemas.lot import BatchLotOut, PoolRequest
from app.schemas.user import FarmerOut
from app.services.fpo_member_service import FpoMemberService, get_fpo_member_service
from app.services.lot_pool_service import LotPoolService

router = APIRouter()          # mounted at /api/v1/pools (lot pooling)
farmers_router = APIRouter()  # mounted at /api/v1/fpo   (membership, Member 1; /lots/pool, Pranay)


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
    service: LotPoolService = Depends(get_lot_pool_service),
):
    """Aggregate multiple lots into a single batch lot. FPO admin only."""
    return await service.pool(user, payload.lot_ids)


@farmers_router.post("/lots/pool", response_model=BatchLotOut, status_code=status.HTTP_201_CREATED)
async def pool_lots(
    payload: PoolRequest,
    user: User = Depends(require_role("FPO_ADMIN")),
    service: LotPoolService = Depends(get_lot_pool_service),
):
    """Pool small farmer lots of one crop into a single FPO batch lot (Pranay)."""
    return await service.pool(user, payload.lot_ids, payload.fpo_id)
