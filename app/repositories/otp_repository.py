"""OTP code repository. Owner: Member 1."""
from abc import abstractmethod
from datetime import datetime
from typing import Optional

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.otp import OtpCode
from app.repositories.base import IRepository, SQLAlchemyBaseRepository


class IOtpRepository(IRepository[OtpCode]):

    @abstractmethod
    async def latest_for_phone(self, phone: str) -> Optional[OtpCode]:
        """Most recently issued OTP for this phone (the only one that verifies)."""

    @abstractmethod
    async def count_issued_since(self, phone: str, since: datetime) -> int:
        """Number of OTPs issued to this phone at or after `since` (throttling)."""

    @abstractmethod
    async def delete_for_phone(self, phone: str) -> None: ...

    @abstractmethod
    async def delete_issued_before(self, phone: str, before: datetime) -> None: ...


class SQLAlchemyOtpRepository(SQLAlchemyBaseRepository[OtpCode], IOtpRepository):
    def __init__(self, session: AsyncSession):
        super().__init__(session, OtpCode)

    async def latest_for_phone(self, phone: str) -> Optional[OtpCode]:
        result = await self.session.execute(
            select(OtpCode)
            .where(OtpCode.phone == phone)
            .order_by(OtpCode.created_at.desc(), OtpCode.id.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def count_issued_since(self, phone: str, since: datetime) -> int:
        result = await self.session.execute(
            select(func.count(OtpCode.id)).where(
                OtpCode.phone == phone, OtpCode.created_at >= since
            )
        )
        return int(result.scalar_one())

    async def delete_for_phone(self, phone: str) -> None:
        await self.session.execute(delete(OtpCode).where(OtpCode.phone == phone))

    async def delete_issued_before(self, phone: str, before: datetime) -> None:
        await self.session.execute(
            delete(OtpCode).where(OtpCode.phone == phone, OtpCode.created_at < before)
        )
