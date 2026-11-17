"""Data-access layer (Repository Pattern). Base classes owned by Member 1."""
from app.repositories.base import (
    IReadRepository,
    IRepository,
    IWriteRepository,
    SQLAlchemyBaseRepository,
)
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

__all__ = [
    "IReadRepository", "IWriteRepository", "IRepository", "SQLAlchemyBaseRepository",
    "IUserRepository", "SQLAlchemyUserRepository",
    "IOtpRepository", "SQLAlchemyOtpRepository",
    "IFpoRepository", "SQLAlchemyFpoRepository",
    "IOfferRepository", "SQLAlchemyOfferRepository",
    "ITransactionRepository", "SQLAlchemyTransactionRepository",
    "IEscrowEventRepository", "SQLAlchemyEscrowEventRepository",
    "IDisputeRepository", "SQLAlchemyDisputeRepository",
]
