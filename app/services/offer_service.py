"""Offer negotiation service."""
from typing import List, Optional, Any, Dict, Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.user import User
from app.models.offer import Offer, OfferLot
from app.schemas.offer import OfferCreate, OfferCounterReq
from app.repositories.offer_repository import IOfferRepository, SQLAlchemyOfferRepository
from app.repositories.transaction_repository import ITransactionRepository, SQLAlchemyTransactionRepository
from app.repositories.transaction_repository import IEscrowEventRepository, SQLAlchemyEscrowEventRepository
from app.services.transaction_service import TransactionService


class OfferService:
    def __init__(
        self,
        offer_repo: IOfferRepository,
        transaction_service: Optional[TransactionService] = None,
    ):
        self.offer_repo = offer_repo
        self.tx_service = transaction_service

    async def create_offer(self, user: User, payload: OfferCreate) -> dict:
        initiator = "BUYER" if user.role.upper() == "BUYER" else "FARMER"
        demand_id = int(payload.demand_id) if payload.demand_id else None
        price_paise = payload.price_paise_per_qtl or payload.offered_price_paise or 200000
        qty_kg = payload.qty_kg or 1000

        new_offer = Offer(
            buyer_id=user.id if user.role.upper() == "BUYER" else 1,
            farmer_id=user.id if user.role.upper() == "FARMER" else None,
            demand_id=demand_id,
            price_paise_per_qtl=price_paise,
            qty_kg=qty_kg,
            initiator=initiator,
            status="OPEN",
            round=1,
        )
        offer = await self.offer_repo.create(new_offer)

        # Link lots
        for lot_id in payload.lot_ids:
            ol = OfferLot(
                offer_id=offer.id,
                lot_id=int(lot_id),
                quantity_allocated_kg=qty_kg // max(1, len(payload.lot_ids)),
            )
            await self.offer_repo.add_offer_lot(ol)

        loaded_offer = await self.offer_repo.get_with_lots(offer.id)
        return _offer_to_dict(loaded_offer or offer)

    async def list_offers(self, user: User) -> List[dict]:
        offers = await self.offer_repo.list_for_user(user.id, user.role)
        return [_offer_to_dict(o) for o in offers]

    async def get_offer(self, offer_id: int) -> dict:
        offer = await self.offer_repo.get_with_lots(offer_id)
        if not offer:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Offer not found")
        return _offer_to_dict(offer)

    async def counter_offer(self, user: User, offer_id: int, payload: OfferCounterReq) -> dict:
        offer = await self.offer_repo.get(offer_id)
        if not offer:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Offer not found")

        if offer.round >= 3:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error": {"code": "MAX_ROUNDS", "message": "Maximum counter-offer rounds reached", "field": None}},
            )

        offer.status = "COUNTERED"
        await self.offer_repo.update(offer)

        initiator = "BUYER" if user.role.upper() == "BUYER" else "FARMER"
        counter_price = payload.price_paise_per_qtl or payload.counter_price_paise or offer.price_paise_per_qtl

        new_offer = Offer(
            buyer_id=offer.buyer_id,
            farmer_id=offer.farmer_id,
            demand_id=offer.demand_id,
            price_paise_per_qtl=counter_price,
            qty_kg=offer.qty_kg,
            initiator=initiator,
            status="OPEN",
            round=offer.round + 1,
            parent_offer_id=offer.id,
            note=payload.note,
        )
        created = await self.offer_repo.create(new_offer)
        return _offer_to_dict(created)

    async def accept_offer(self, user: User, offer_id: int) -> Any:
        offer = await self.offer_repo.get(offer_id)
        if not offer:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Offer not found")

        offer.status = "ACCEPTED"
        await self.offer_repo.update(offer)

        if self.tx_service:
            txn = await self.tx_service.create_transaction_for_offer(user, offer)
            return txn

        return _offer_to_dict(offer)

    async def reject_offer(self, user: User, offer_id: int) -> dict:
        offer = await self.offer_repo.get(offer_id)
        if not offer:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Offer not found")

        offer.status = "REJECTED"
        await self.offer_repo.update(offer)
        return _offer_to_dict(offer)

    async def get_offer_thread(self, user: User, offer_id: int) -> List[dict]:
        thread = await self.offer_repo.get_offer_thread(offer_id)
        if not thread:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Offer not found")
        return [_offer_to_dict(o) for o in thread]


def _offer_to_dict(offer: Offer) -> dict:
    lots_data = []
    if hasattr(offer, "lots") and offer.lots:
        for ol in offer.lots:
            lots_data.append({
                "lot_id": str(ol.lot_id),
                "qty_allocated_kg": ol.quantity_allocated_kg,
            })

    return {
        "id": str(offer.id),
        "demand_id": str(offer.demand_id) if offer.demand_id else None,
        "buyer_id": str(offer.buyer_id),
        "farmer_id": str(offer.farmer_id) if offer.farmer_id else None,
        "pool_id": str(offer.pool_id) if offer.pool_id else None,
        "price_paise_per_qtl": offer.price_paise_per_qtl,
        "offered_price_paise": offer.price_paise_per_qtl,
        "qty_kg": offer.qty_kg,
        "round": offer.round,
        "parent_offer_id": str(offer.parent_offer_id) if offer.parent_offer_id else None,
        "initiator": offer.initiator,
        "status": offer.status,
        "expires_at": offer.expires_at,
        "created_at": offer.created_at,
        "lots": lots_data,
        "note": offer.note,
    }


# Backward-compatible helper functions delegating to OfferService
def _get_service(db: AsyncSession) -> OfferService:
    offer_repo = SQLAlchemyOfferRepository(db)
    txn_repo = SQLAlchemyTransactionRepository(db)
    event_repo = SQLAlchemyEscrowEventRepository(db)
    tx_service = TransactionService(txn_repo, event_repo, offer_repo)
    return OfferService(offer_repo, tx_service)


async def create_offer(db: AsyncSession, user: User, payload: OfferCreate) -> dict:
    return await _get_service(db).create_offer(user, payload)


async def list_offers(db: AsyncSession, user: User) -> List[dict]:
    return await _get_service(db).list_offers(user)


async def accept_offer(db: AsyncSession, user: User, offer_id: int):
    return await _get_service(db).accept_offer(user, offer_id)


async def reject_offer(db: AsyncSession, user: User, offer_id: int) -> dict:
    return await _get_service(db).reject_offer(user, offer_id)


async def counter_offer(db: AsyncSession, user: User, offer_id: int, payload: OfferCounterReq) -> dict:
    return await _get_service(db).counter_offer(user, offer_id, payload)


async def get_offer_thread(db: AsyncSession, user: User, offer_id: int) -> List[dict]:
    return await _get_service(db).get_offer_thread(user, offer_id)
