from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
from app.models.user import User
from app.models.transaction import Transaction, EscrowEvent
from app.schemas.transaction import FSMTransitionReq
from datetime import datetime

async def get_transaction(db: AsyncSession, user: User, transaction_id: int):
    # TODO check if user has access (buyer or farmer of the offer)
    result = await db.execute(select(Transaction).where(Transaction.id == transaction_id))
    txn = result.scalar_one_or_none()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
        
    events_result = await db.execute(select(EscrowEvent).where(EscrowEvent.transaction_id == txn.id).order_by(EscrowEvent.created_at))
    txn.events = events_result.scalars().all()
    return txn

async def transition_state(db: AsyncSession, user: User, transaction_id: int, payload: FSMTransitionReq):
    txn = await get_transaction(db, user, transaction_id)
    
    status_map = {
        'DEPOSIT_PAID': ('PENDING_BUYER_DEPOSIT', 'DEPOSIT_HELD'),
        'DISPATCHED': ('DEPOSIT_HELD', 'IN_TRANSIT'),
        'ARRIVED': ('IN_TRANSIT', 'ARRIVED_PENDING_INSPECTION'),
        'INSPECTED_OK': ('ARRIVED_PENDING_INSPECTION', 'INSPECTION_PASSED'),
        'INSPECTED_REJECT': ('ARRIVED_PENDING_INSPECTION', 'DISPUTED_QUALITY'),
        'FUNDS_TRANSFER': ('INSPECTION_PASSED', 'FUNDS_RELEASED'),
        'NO_SHOW': ('DEPOSIT_HELD', 'DISPUTED_NO_SHOW'),
        'REFUND': ('DISPUTED_QUALITY', 'CANCELLED_REFUNDED'),
    }
    
    if payload.action not in status_map:
        raise HTTPException(status_code=400, detail="Invalid action")
        
    expected_from, to_status = status_map[payload.action]
    
    if txn.status != expected_from:
        raise HTTPException(
            status_code=409, 
            detail={"error": {"code": "INVALID_TRANSITION", "message": f"Cannot transition from {txn.status} using {payload.action}", "field": None}}
        )
        
    # Log event
    event = EscrowEvent(
        transaction_id=txn.id,
        status_from=txn.status,
        status_to=to_status,
        actor_id=user.id,
        note=payload.note
    )
    db.add(event)
    
    # Update status
    txn.status = to_status
    await db.commit()
    await db.refresh(txn)
    
    # Reload with events
    return await get_transaction(db, user, transaction_id)
