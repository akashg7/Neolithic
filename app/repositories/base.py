"""Generic Repository Pattern — the data-access foundation every module builds on.

Owner: Member 1 (LLD_MEMBER_1_AUTH_AND_REPOSITORY.md §4, Pattern 1).

Interfaces are split (ISP) so a service that only reads never depends on
write methods:

    IReadRepository[T]   get_by_id, list
    IWriteRepository[T]  create, update, delete, commit
    IRepository[T]       both of the above

`SQLAlchemyBaseRepository[T]` is the concrete async implementation. Domain
repositories (UserRepository, LotRepository, ...) subclass it and add their
own queries.

Transaction boundary: `create`/`update`/`delete` only *flush* (so generated
IDs are available immediately). The request-scoped session from `get_db`
commits at the end of the request; a service that must persist something
before raising an HTTP error (e.g. an OTP attempt counter) calls `commit()`
explicitly. This keeps multi-entity writes (User + Farmer profile) atomic.
"""
from abc import ABC, abstractmethod
from typing import Generic, Optional, Sequence, Type, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


class IReadRepository(ABC, Generic[T]):
    """Read-only data access for an entity type."""

    @abstractmethod
    async def get_by_id(self, id: int) -> Optional[T]: ...

    @abstractmethod
    async def list(self, skip: int = 0, limit: int = 100) -> Sequence[T]: ...


class IWriteRepository(ABC, Generic[T]):
    """Write-side data access for an entity type."""

    @abstractmethod
    async def create(self, entity: T) -> T: ...

    @abstractmethod
    async def update(self, entity: T) -> T: ...

    @abstractmethod
    async def delete(self, id: int) -> bool: ...

    @abstractmethod
    async def commit(self) -> None: ...


class IRepository(IReadRepository[T], IWriteRepository[T], ABC):
    """Full CRUD contract = read + write."""


class SQLAlchemyBaseRepository(IRepository[T]):
    """Concrete async SQLAlchemy implementation of `IRepository[T]`."""

    def __init__(self, session: AsyncSession, model_cls: Type[T]):
        self.session = session
        self.model_cls = model_cls

    async def get_by_id(self, id: int) -> Optional[T]:
        return await self.session.get(self.model_cls, id)

    async def list(self, skip: int = 0, limit: int = 100) -> Sequence[T]:
        result = await self.session.execute(
            select(self.model_cls).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def create(self, entity: T) -> T:
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def update(self, entity: T) -> T:
        merged = await self.session.merge(entity)
        await self.session.flush()
        return merged

    async def delete(self, id: int) -> bool:
        entity = await self.get_by_id(id)
        if entity is None:
            return False
        await self.session.delete(entity)
        await self.session.flush()
        return True

    async def commit(self) -> None:
        await self.session.commit()
