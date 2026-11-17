"""FastAPI providers that bind repository *interfaces* to concrete classes (DIP).

Routers and services depend on these providers / the abstract interfaces. A
test can swap any of them with
`app.dependency_overrides[get_user_repository] = lambda: InMemoryUserRepo()`.
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.repositories.fpo_repository import IFpoRepository, SQLAlchemyFpoRepository
from app.repositories.otp_repository import IOtpRepository, SQLAlchemyOtpRepository
from app.repositories.user_repository import IUserRepository, SQLAlchemyUserRepository
from app.repositories.offer_repository import IOfferRepository, SQLAlchemyOfferRepository
from app.repositories.transaction_repository import (
    ITransactionRepository,
    SQLAlchemyTransactionRepository,
    IEscrowEventRepository,
    SQLAlchemyEscrowEventRepository,
    IDisputeRepository,
    SQLAlchemyDisputeRepository,
)


def get_user_repository(db: AsyncSession = Depends(get_db)) -> IUserRepository:
    return SQLAlchemyUserRepository(db)


def get_otp_repository(db: AsyncSession = Depends(get_db)) -> IOtpRepository:
    return SQLAlchemyOtpRepository(db)


def get_fpo_repository(db: AsyncSession = Depends(get_db)) -> IFpoRepository:
    return SQLAlchemyFpoRepository(db)


def get_offer_repository(db: AsyncSession = Depends(get_db)) -> IOfferRepository:
    return SQLAlchemyOfferRepository(db)


def get_transaction_repository(db: AsyncSession = Depends(get_db)) -> ITransactionRepository:
    return SQLAlchemyTransactionRepository(db)


def get_escrow_event_repository(db: AsyncSession = Depends(get_db)) -> IEscrowEventRepository:
    return SQLAlchemyEscrowEventRepository(db)


def get_dispute_repository(db: AsyncSession = Depends(get_db)) -> IDisputeRepository:
    return SQLAlchemyDisputeRepository(db)
