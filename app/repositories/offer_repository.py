"""Offer repository interface and SQLAlchemy implementation."""
from abc import abstractmethod
from typing import Optional, Sequence
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.offer import Offer, OfferLot
from app.repositories.base import IRepository, SQLAlchemyBaseRepository


class IOfferRepository(IRepository[Offer]):
    async def get(self, id: int) -> Optional[Offer]:
        return await self.get_by_id(id)

    @abstractmethod
    async def list_for_user(self, user_id: int, role: str) -> Sequence[Offer]:
        """List offers where the user is buyer or farmer."""
        pass

    @abstractmethod
    async def get_with_lots(self, offer_id: int) -> Optional[Offer]:
        """Get offer with loaded lots allocations."""
        pass

    @abstractmethod
    async def get_offer_thread(self, offer_id: int) -> Sequence[Offer]:
        """Get full negotiation history starting from the root offer, oldest first."""
        pass

    @abstractmethod
    async def add_offer_lot(self, offer_lot: OfferLot) -> OfferLot:
        """Associate a lot with an offer."""
        pass


class SQLAlchemyOfferRepository(SQLAlchemyBaseRepository[Offer], IOfferRepository):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Offer)

    async def get(self, id: int) -> Optional[Offer]:
        return await self.get_by_id(id)

    async def list_for_user(self, user_id: int, role: str) -> Sequence[Offer]:
        query = select(Offer).options(selectinload(Offer.lots))
        if role.upper() == "BUYER":
            query = query.where(Offer.buyer_id == user_id)
        else:
            query = query.where(Offer.farmer_id == user_id)
        result = await self.session.execute(query.order_by(Offer.created_at.desc()))
        return result.scalars().all()

    async def get_with_lots(self, offer_id: int) -> Optional[Offer]:
        query = select(Offer).options(selectinload(Offer.lots)).where(Offer.id == offer_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_offer_thread(self, offer_id: int) -> Sequence[Offer]:
        # Eager-load lots on every hop: a lazy load inside async code raises
        # MissingGreenlet when the DTO reads `offer.lots`.
        current = await self.get_with_lots(offer_id)
        if not current:
            return []

        ancestors = [current]
        while current.parent_offer_id:
            parent = await self.get_with_lots(current.parent_offer_id)
            if not parent:
                break
            ancestors.append(parent)
            current = parent
        
        ancestors.reverse()  # Oldest first
        return ancestors

    async def add_offer_lot(self, offer_lot: OfferLot) -> OfferLot:
        self.session.add(offer_lot)
        await self.session.flush()
        return offer_lot
