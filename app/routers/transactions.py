from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.transaction import (
    TransactionOut,
    FSMTransitionReq,
    DepositReq,
    DispatchReq,
    InspectReq,
    ReleaseReq,
    EscrowEventOut,
)
from app.dependencies.escrow import get_transaction_service
from app.services.transaction_service import TransactionService

router = APIRouter()


@router.get("/{transaction_id}", response_model=TransactionOut)
async def get_transaction(
    transaction_id: int,
    user: User = Depends(get_current_user),
    service: TransactionService = Depends(get_transaction_service),
):
    """Get transaction status + events."""
    return await service.get_transaction(user, transaction_id)


@router.get("/{transaction_id}/events", response_model=List[EscrowEventOut])
async def get_transaction_events(
    transaction_id: int,
    user: User = Depends(get_current_user),
    service: TransactionService = Depends(get_transaction_service),
):
    """Get append-only escrow event timeline for this transaction."""
    txn = await service.get_transaction(user, transaction_id)
    return txn.events or []


@router.post("/{transaction_id}/deposit", response_model=TransactionOut)
async def deposit_funds(
    transaction_id: int,
    payload: Optional[DepositReq] = None,
    user: User = Depends(get_current_user),
    service: TransactionService = Depends(get_transaction_service),
):
    """Buyer deposits funds; transitions to DEPOSIT_HELD."""
    return await service.deposit(user, transaction_id, payload)


@router.post("/{transaction_id}/dispatch", response_model=TransactionOut)
async def dispatch_cargo(
    transaction_id: int,
    payload: Optional[DispatchReq] = None,
    user: User = Depends(get_current_user),
    service: TransactionService = Depends(get_transaction_service),
):
    """Farmer dispatches cargo; transitions to IN_TRANSIT."""
    return await service.dispatch(user, transaction_id, payload)


@router.post("/{transaction_id}/inspect", response_model=TransactionOut)
async def inspect_cargo(
    transaction_id: int,
    payload: Optional[InspectReq] = None,
    user: User = Depends(get_current_user),
    service: TransactionService = Depends(get_transaction_service),
):
    """Buyer verifies quality; transitions to INSPECTED."""
    return await service.inspect(user, transaction_id, payload)


@router.post("/{transaction_id}/release", response_model=TransactionOut)
async def release_funds(
    transaction_id: int,
    payload: Optional[ReleaseReq] = None,
    user: User = Depends(get_current_user),
    service: TransactionService = Depends(get_transaction_service),
):
    """Releases escrow payout to farmer (FUNDS_RELEASED)."""
    return await service.release(user, transaction_id, payload)


@router.post("/{transaction_id}/transition", response_model=TransactionOut)
async def transition_transaction(
    transaction_id: int,
    payload: FSMTransitionReq,
    user: User = Depends(get_current_user),
    service: TransactionService = Depends(get_transaction_service),
):
    """Move escrow state machine forward using State Pattern."""
    return await service.transition_state(user, transaction_id, payload)
