from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.offer import OfferDto, OfferCreate, OfferCounterReq
from app.services import offer_service

router = APIRouter()

@router.post("", response_model=OfferDto, status_code=status.HTTP_201_CREATED)
async def create_offer(
    payload: OfferCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new offer."""
    return await offer_service.create_offer(db, user, payload)

@router.get("", response_model=List[OfferDto])
async def list_offers(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List offers relevant to the user (actor-scoped)."""
    return await offer_service.list_offers(db, user)

@router.post("/{offer_id}/accept", response_model=OfferDto)
async def accept_offer(
    offer_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Accept an offer. Generates a transaction."""
    return await offer_service.accept_offer(db, user, offer_id)

@router.post("/{offer_id}/reject", response_model=OfferDto)
async def reject_offer(
    offer_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reject an offer."""
    return await offer_service.reject_offer(db, user, offer_id)

@router.post("/{offer_id}/counter", response_model=OfferDto)
async def counter_offer(
    offer_id: int,
    payload: OfferCounterReq,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Counter an offer (creates new child offer). Max 3 rounds."""
    return await offer_service.counter_offer(db, user, offer_id, payload)

@router.get("/{offer_id}/thread", response_model=List[OfferDto])
async def get_offer_thread(
    offer_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the full counter chain, oldest first."""
    return await offer_service.get_offer_thread(db, user, offer_id)
