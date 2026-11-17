from typing import List, Union
from fastapi import APIRouter, Depends, HTTPException, status
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.offer import OfferDto, OfferCreate, OfferCounterReq
from app.schemas.transaction import TransactionOut
from app.dependencies.escrow import get_offer_service
from app.services.offer_service import OfferService

router = APIRouter()


@router.post("", response_model=OfferDto, status_code=status.HTTP_201_CREATED)
async def create_offer(
    payload: OfferCreate,
    user: User = Depends(get_current_user),
    service: OfferService = Depends(get_offer_service),
):
    """Create a new offer on farmer lot(s)."""
    return await service.create_offer(user, payload)


@router.get("", response_model=List[OfferDto])
async def list_offers(
    user: User = Depends(get_current_user),
    service: OfferService = Depends(get_offer_service),
):
    """List offers relevant to the user (actor-scoped)."""
    return await service.list_offers(user)


@router.post("/{offer_id}/accept", response_model=Union[TransactionOut, OfferDto])
async def accept_offer(
    offer_id: int,
    user: User = Depends(get_current_user),
    service: OfferService = Depends(get_offer_service),
):
    """Accept an offer. Spawns an Escrow Transaction in CREATED state."""
    return await service.accept_offer(user, offer_id)


@router.post("/{offer_id}/reject", response_model=OfferDto)
async def reject_offer(
    offer_id: int,
    user: User = Depends(get_current_user),
    service: OfferService = Depends(get_offer_service),
):
    """Reject an offer."""
    return await service.reject_offer(user, offer_id)


@router.post("/{offer_id}/counter", response_model=OfferDto)
async def counter_offer(
    offer_id: int,
    payload: OfferCounterReq,
    user: User = Depends(get_current_user),
    service: OfferService = Depends(get_offer_service),
):
    """Counter an offer (creates new child offer). Max 3 rounds."""
    return await service.counter_offer(user, offer_id, payload)


@router.get("/{offer_id}/thread", response_model=List[OfferDto])
async def get_offer_thread(
    offer_id: int,
    user: User = Depends(get_current_user),
    service: OfferService = Depends(get_offer_service),
):
    """Get the full counter chain, oldest first."""
    return await service.get_offer_thread(user, offer_id)
