from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from app.models.user import User
from app.models.offer import Offer, OfferLot
from app.schemas.offer import OfferCreate, OfferCounterReq
from typing import List

async def create_offer(db: AsyncSession, user: User, payload: OfferCreate) -> dict:
    initiator = "BUYER" if user.role == "BUYER" else "FARMER"
    # Basic validation
    new_offer = Offer(
        buyer_id=user.id if user.role == "BUYER" else 1, # Dummy logic if farmer initiates without explicit buyer
        farmer_id=user.id if user.role == "FARMER" else None,
        demand_id=int(payload.demand_id) if payload.demand_id else None,
        price_paise_per_qtl=payload.price_paise_per_qtl,
        qty_kg=payload.qty_kg,
        initiator=initiator,
        status="OPEN",
        round=1
    )
    db.add(new_offer)
    await db.commit()
    await db.refresh(new_offer)
    
    # Add offer lots
    for lot_id_str in payload.lot_ids:
        ol = OfferLot(offer_id=new_offer.id, lot_id=int(lot_id_str), quantity_allocated_kg=payload.qty_kg)
        db.add(ol)
    
    await db.commit()
    await db.refresh(new_offer)
    
    return _offer_to_dict(new_offer)

async def list_offers(db: AsyncSession, user: User) -> List[dict]:
    if user.role == "BUYER":
        query = select(Offer).where(Offer.buyer_id == user.id)
    else:
        query = select(Offer).where(Offer.farmer_id == user.id)
        
    result = await db.execute(query)
    offers = result.scalars().all()
    return [_offer_to_dict(o) for o in offers]

async def accept_offer(db: AsyncSession, user: User, offer_id: int) -> dict:
    offer = await db.get(Offer, offer_id)
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    offer.status = "ACCEPTED"
    await db.commit()
    return _offer_to_dict(offer)

async def reject_offer(db: AsyncSession, user: User, offer_id: int) -> dict:
    offer = await db.get(Offer, offer_id)
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    offer.status = "REJECTED"
    await db.commit()
    return _offer_to_dict(offer)

async def counter_offer(db: AsyncSession, user: User, offer_id: int, payload: OfferCounterReq) -> dict:
    offer = await db.get(Offer, offer_id)
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    if offer.round >= 3:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": "MAX_ROUNDS", "message": "Maximum counter-offer rounds reached", "field": None}}
        )
        
    offer.status = "COUNTERED"
    
    initiator = "BUYER" if user.role == "BUYER" else "FARMER"
    new_offer = Offer(
        buyer_id=offer.buyer_id,
        farmer_id=offer.farmer_id,
        demand_id=offer.demand_id,
        price_paise_per_qtl=payload.price_paise_per_qtl,
        qty_kg=offer.qty_kg,
        initiator=initiator,
        status="OPEN",
        round=offer.round + 1,
        parent_offer_id=offer.id,
        note=payload.note
    )
    db.add(new_offer)
    await db.commit()
    await db.refresh(new_offer)
    return _offer_to_dict(new_offer)

async def get_offer_thread(db: AsyncSession, user: User, offer_id: int) -> List[dict]:
    # Very naive implementation for the thread
    offer = await db.get(Offer, offer_id)
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
        
    thread = [offer]
    current = offer
    while current.parent_offer_id:
        current = await db.get(Offer, current.parent_offer_id)
        if current:
            thread.append(current)
        else:
            break
            
    thread.reverse() # oldest first
    return [_offer_to_dict(o) for o in thread]

def _offer_to_dict(offer: Offer) -> dict:
    return {
        "id": str(offer.id),
        "demand_id": str(offer.demand_id) if offer.demand_id else None,
        "buyer_id": str(offer.buyer_id),
        "farmer_id": str(offer.farmer_id) if offer.farmer_id else None,
        "pool_id": str(offer.pool_id) if offer.pool_id else None,
        "price_paise_per_qtl": offer.price_paise_per_qtl,
        "qty_kg": offer.qty_kg,
        "round": offer.round,
        "parent_offer_id": str(offer.parent_offer_id) if offer.parent_offer_id else None,
        "initiator": offer.initiator,
        "status": offer.status,
        "expires_at": offer.expires_at,
        "created_at": offer.created_at,
        "lots": [], # Mock for now
        "note": offer.note
    }
