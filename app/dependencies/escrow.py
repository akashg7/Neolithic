"""FastAPI Dependency Providers for Offers, Transactions & Escrow State Machine (DIP).

Allows routes and tests to swap in-memory services or mock repositories seamlessly.
"""
from fastapi import Depends
from app.repositories.offer_repository import IOfferRepository
from app.repositories.transaction_repository import (
    ITransactionRepository,
    IEscrowEventRepository,
    IDisputeRepository,
)
from app.dependencies.repositories import (
    get_offer_repository,
    get_transaction_repository,
    get_escrow_event_repository,
    get_dispute_repository,
)
from app.services.transaction_service import TransactionService
from app.services.offer_service import OfferService
from app.services.dispute_service import DisputeService


def get_transaction_service(
    txn_repo: ITransactionRepository = Depends(get_transaction_repository),
    event_repo: IEscrowEventRepository = Depends(get_escrow_event_repository),
    offer_repo: IOfferRepository = Depends(get_offer_repository),
) -> TransactionService:
    return TransactionService(txn_repo, event_repo, offer_repo)


def get_offer_service(
    offer_repo: IOfferRepository = Depends(get_offer_repository),
    tx_service: TransactionService = Depends(get_transaction_service),
) -> OfferService:
    return OfferService(offer_repo, tx_service)


def get_dispute_service(
    dispute_repo: IDisputeRepository = Depends(get_dispute_repository),
    tx_service: TransactionService = Depends(get_transaction_service),
) -> DisputeService:
    return DisputeService(dispute_repo, tx_service)

