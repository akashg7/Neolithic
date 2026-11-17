"""Disputes router."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.dispute import DisputeCreate, DisputeOut, DisputeUpdate
from app.dependencies.escrow import get_dispute_service
from app.services.dispute_service import DisputeService

router = APIRouter()


@router.post("", response_model=DisputeOut, status_code=status.HTTP_201_CREATED)
async def raise_dispute(
    payload: DisputeCreate,
    user: User = Depends(get_current_user),
    service: DisputeService = Depends(get_dispute_service),
):
    """Raise a dispute on an escrow transaction. Halts fund release and transitions state to DISPUTED."""
    return await service.raise_dispute(user, payload)


@router.get("", response_model=List[DisputeOut])
async def list_disputes(
    user: User = Depends(get_current_user),
    service: DisputeService = Depends(get_dispute_service),
):
    """List disputes relevant to current user."""
    return await service.list_disputes(user)


@router.get("/{dispute_id}", response_model=DisputeOut)
async def get_dispute(
    dispute_id: int,
    user: User = Depends(get_current_user),
    service: DisputeService = Depends(get_dispute_service),
):
    """Get dispute by ID."""
    return await service.get_dispute(user, dispute_id)


@router.patch("/{dispute_id}", response_model=DisputeOut)
async def update_dispute(
    dispute_id: int,
    payload: DisputeUpdate,
    user: User = Depends(get_current_user),
    service: DisputeService = Depends(get_dispute_service),
):
    """Update dispute status (e.g. investigating, resolved, dismissed)."""
    return await service.update_dispute(user, dispute_id, payload)
