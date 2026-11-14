"""FastAPI providers that bind repository *interfaces* to concrete classes (DIP).

Routers and services depend on these providers / the abstract interfaces. A
test can swap any of them with
`app.dependency_overrides[get_user_repository] = lambda: InMemoryUserRepo()`.
Owner: Member 1.
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.repositories.fpo_repository import IFpoRepository, SQLAlchemyFpoRepository
from app.repositories.otp_repository import IOtpRepository, SQLAlchemyOtpRepository
from app.repositories.user_repository import IUserRepository, SQLAlchemyUserRepository


def get_user_repository(db: AsyncSession = Depends(get_db)) -> IUserRepository:
    return SQLAlchemyUserRepository(db)


def get_otp_repository(db: AsyncSession = Depends(get_db)) -> IOtpRepository:
    return SQLAlchemyOtpRepository(db)


def get_fpo_repository(db: AsyncSession = Depends(get_db)) -> IFpoRepository:
    return SQLAlchemyFpoRepository(db)
