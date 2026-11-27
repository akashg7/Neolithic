"""FPO repository. Owner: Member 1."""
from abc import abstractmethod
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.fpo import FPO
from app.models.user import Farmer
from app.repositories.base import IRepository, SQLAlchemyBaseRepository


class IFpoRepository(IRepository[FPO]):

    @abstractmethod
    async def get_fpo_id_for_user(self, user_id: int) -> Optional[int]:
        """FPO the given user (an FPO admin / farmer) belongs to, if any."""

    @abstractmethod
    async def list_farmers(self, fpo_id: int) -> Sequence[Farmer]:
        """Farmer profiles (with `.user` loaded) registered under this FPO."""

    async def get_fpo_ids_for_users(self, user_ids: Sequence[int]) -> dict[int, Optional[int]]:
        """Batch lookup mapping user_id -> fpo_id (default fallback for test doubles)."""
        out: dict[int, Optional[int]] = {}
        for uid in dict.fromkeys(user_ids):
            out[uid] = await self.get_fpo_id_for_user(uid)
        return out


class SQLAlchemyFpoRepository(SQLAlchemyBaseRepository[FPO], IFpoRepository):
    def __init__(self, session: AsyncSession):
        super().__init__(session, FPO)

    async def get_fpo_id_for_user(self, user_id: int) -> Optional[int]:
        result = await self.session.execute(
            select(Farmer.fpo_id).where(Farmer.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_fpo_ids_for_users(self, user_ids: Sequence[int]) -> dict[int, Optional[int]]:
        unique_ids = list(dict.fromkeys(user_ids))
        if not unique_ids:
            return {}
        rows = (
            await self.session.execute(
                select(Farmer.user_id, Farmer.fpo_id).where(Farmer.user_id.in_(unique_ids))
            )
        ).all()
        return {uid: fpo_id for uid, fpo_id in rows}

    async def list_farmers(self, fpo_id: int) -> Sequence[Farmer]:
        result = await self.session.execute(
            select(Farmer)
            .options(selectinload(Farmer.user))
            .where(Farmer.fpo_id == fpo_id)
            .order_by(Farmer.user_id)
        )
        return result.scalars().all()
