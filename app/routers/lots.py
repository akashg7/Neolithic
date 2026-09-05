from typing import Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import get_current_user, require_role
from app.models.user import User
from app.schemas.lot import (
    LotCreate, LotOut, SelfAssayRequest, SelfAssayResponse,
    PriceSuggestionResponse, LotMatchesResponse,
)
from app.services import lot_service

router = APIRouter()


@router.post("", response_model=LotOut, status_code=status.HTTP_201_CREATED)
async def create_lot(
    payload: LotCreate,
    user: User = Depends(require_role("farmer", "fpo_admin")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new lot. Auto-calls Price Engine for price band."""
    return await lot_service.create_lot(db, user, payload)


@router.get("", response_model=list[LotOut])
async def list_lots(
    status: Optional[str] = None,
    user: User = Depends(require_role("farmer", "fpo_admin")),
    db: AsyncSession = Depends(get_db),
):
    """List lots owned by the current farmer, optionally filtered by status."""
    return await lot_service.list_lots(db, user, status)


@router.get("/{lot_id}", response_model=LotOut)
async def get_lot(
    lot_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single lot. Checks ownership or buyer-has-offer access."""
    return await lot_service.get_lot(db, user, lot_id)


@router.post("/{lot_id}/self-assay", response_model=SelfAssayResponse)
async def submit_self_assay(
    lot_id: int,
    payload: SelfAssayRequest,
    user: User = Depends(require_role("farmer", "fpo_admin")),
    db: AsyncSession = Depends(get_db),
):
    """Submit self-assay quality answers for a lot. Returns computed grade."""
    return await lot_service.submit_self_assay(db, user, lot_id, payload)


@router.get("/{lot_id}/price-suggestion", response_model=PriceSuggestionResponse)
async def get_price_suggestion(
    lot_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get price band + SELL/HOLD/NO_ADVICE recommendation for a lot."""
    return await lot_service.get_price_suggestion(db, user, lot_id)


@router.get("/{lot_id}/matches", response_model=LotMatchesResponse)
async def get_lot_matches(
    lot_id: int,
    user: User = Depends(require_role("farmer", "fpo_admin")),
    db: AsyncSession = Depends(get_db),
):
    """Find matching buyer demands for a lot."""
    return await lot_service.get_lot_matches(db, user, lot_id)
