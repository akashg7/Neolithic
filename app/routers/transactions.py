from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.transaction import TransactionOut, FSMTransitionReq
from app.services import transaction_service

router = APIRouter()

@router.get("/{transaction_id}", response_model=TransactionOut)
async def get_transaction(
    transaction_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get transaction status + events."""
    return await transaction_service.get_transaction(db, user, transaction_id)

@router.post("/{transaction_id}/transition", response_model=TransactionOut)
async def transition_transaction(
    transaction_id: int,
    payload: FSMTransitionReq,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Move escrow state machine forward."""
    return await transaction_service.transition_state(db, user, transaction_id, payload)
