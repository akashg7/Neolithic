"""Data-access layer (Repository Pattern). Base classes owned by Member 1.

Other modules should subclass `SQLAlchemyBaseRepository[T]` for their own
entities, e.g.:

    class LotRepository(SQLAlchemyBaseRepository[Lot]):
        def __init__(self, session):
            super().__init__(session, Lot)
"""
from app.repositories.base import (
    IReadRepository,
    IRepository,
    IWriteRepository,
    SQLAlchemyBaseRepository,
)
from app.repositories.fpo_repository import IFpoRepository, SQLAlchemyFpoRepository
from app.repositories.otp_repository import IOtpRepository, SQLAlchemyOtpRepository
from app.repositories.user_repository import IUserRepository, SQLAlchemyUserRepository

__all__ = [
    "IReadRepository", "IWriteRepository", "IRepository", "SQLAlchemyBaseRepository",
    "IUserRepository", "SQLAlchemyUserRepository",
    "IOtpRepository", "SQLAlchemyOtpRepository",
    "IFpoRepository", "SQLAlchemyFpoRepository",
]
