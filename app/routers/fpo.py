from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import require_role
from app.models.user import User
from app.schemas.lot import BatchLotOut
from app.services import fpo_service

router = APIRouter()


class AggregateRequest(BaseModel):
    lot_ids: list[int] = Field(..., min_length=1)


@router.post("/aggregate", response_model=BatchLotOut, status_code=status.HTTP_201_CREATED)
async def aggregate_lots(
    payload: AggregateRequest,
    user: User = Depends(require_role("fpo_admin")),
    db: AsyncSession = Depends(get_db),
):
    """Aggregate multiple lots into a single batch lot. FPO admin only."""
    return await fpo_service.aggregate_lots(db, user, payload.lot_ids)
