"""Lot and Commodity repositories. Owner: Pranay.

Built on Member 1's generic `SQLAlchemyBaseRepository`. Services depend on the
interfaces (`ILotRepository`, `ICommodityRepository`), never on SQLAlchemy.
"""
from abc import abstractmethod
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lot import BatchLotMember, Lot
from app.models.reference import Commodity
from app.repositories.base import IRepository, SQLAlchemyBaseRepository


class ILotRepository(IRepository[Lot]):

    @abstractmethod
    async def list_for_farmer(self, farmer_id: int, status: Optional[str] = None) -> Sequence[Lot]:
        """Lots owned by this farmer, newest first."""

    @abstractmethod
    async def get_many(self, lot_ids: Sequence[int], lock: bool = False) -> Sequence[Lot]:
        """Lots with these IDs. Missing IDs are simply absent from the result.

        lock=True takes a row lock (SELECT ... FOR UPDATE) until the request's
        transaction ends, so two requests can't pool the same lot at once.
        """

    @abstractmethod
    async def add_batch_member(self, member: BatchLotMember) -> BatchLotMember:
        """Record that a source lot was pooled into a batch lot."""


class ICommodityRepository(IRepository[Commodity]):

    @abstractmethod
    async def get_name(self, commodity_id: int) -> Optional[str]: ...


class SQLAlchemyLotRepository(SQLAlchemyBaseRepository[Lot], ILotRepository):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Lot)

    async def list_for_farmer(self, farmer_id: int, status: Optional[str] = None) -> Sequence[Lot]:
        query = select(Lot).where(Lot.farmer_id == farmer_id)
        if status:
            query = query.where(Lot.status == status)
        result = await self.session.execute(query.order_by(Lot.created_at.desc()))
        return result.scalars().all()

    async def get_many(self, lot_ids: Sequence[int], lock: bool = False) -> Sequence[Lot]:
        if not lot_ids:
            return []
        query = select(Lot).where(Lot.id.in_(list(lot_ids))).order_by(Lot.id)
        if lock:
            query = query.with_for_update()
        result = await self.session.execute(query)
        return result.scalars().all()

    async def add_batch_member(self, member: BatchLotMember) -> BatchLotMember:
        self.session.add(member)
        await self.session.flush()
        return member


class SQLAlchemyCommodityRepository(SQLAlchemyBaseRepository[Commodity], ICommodityRepository):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Commodity)

    async def get_name(self, commodity_id: int) -> Optional[str]:
        result = await self.session.execute(
            select(Commodity.name).where(Commodity.id == commodity_id)
        )
        return result.scalar_one_or_none()
