"""User aggregate repository (User + Farmer/Buyer profiles). Owner: Member 1."""
from abc import abstractmethod
from typing import Optional, Union

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import Buyer, Farmer, User
from app.repositories.base import IRepository, SQLAlchemyBaseRepository

Profile = Union[Farmer, Buyer]


class IUserRepository(IRepository[User]):
    """User-specific queries on top of generic CRUD."""

    @abstractmethod
    async def get_by_phone(self, phone: str) -> Optional[User]: ...

    @abstractmethod
    async def get_with_profiles(self, user_id: int) -> Optional[User]: ...

    @abstractmethod
    async def add_profile(self, profile: Profile) -> Profile: ...


class SQLAlchemyUserRepository(SQLAlchemyBaseRepository[User], IUserRepository):
    def __init__(self, session: AsyncSession):
        super().__init__(session, User)

    async def get_by_phone(self, phone: str) -> Optional[User]:
        result = await self.session.execute(select(User).where(User.phone == phone))
        return result.scalar_one_or_none()

    async def get_with_profiles(self, user_id: int) -> Optional[User]:
        result = await self.session.execute(
            select(User)
            .options(selectinload(User.farmer_profile), selectinload(User.buyer_profile))
            .where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def add_profile(self, profile: Profile) -> Profile:
        self.session.add(profile)
        await self.session.flush()
        return profile
