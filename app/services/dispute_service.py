"""Dispute Service for escrow conflict arbitration."""
from typing import Optional, Sequence, List
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.user import User
from app.models.dispute import Dispute
from app.schemas.dispute import DisputeCreate, DisputeUpdate
from app.repositories.transaction_repository import (
    IDisputeRepository,
    SQLAlchemyDisputeRepository,
    ITransactionRepository,
    SQLAlchemyTransactionRepository,
    IEscrowEventRepository,
    SQLAlchemyEscrowEventRepository,
)
from app.services.transaction_service import TransactionService


class DisputeService:
    def __init__(
        self,
        dispute_repo: IDisputeRepository,
        transaction_service: TransactionService,
    ):
        self.dispute_repo = dispute_repo
        self.tx_service = transaction_service

    async def raise_dispute(self, user: User, payload: DisputeCreate) -> Dispute:
        """Halts release and transitions escrow state to DISPUTED via State Pattern."""
        # This will validate state transition legality and notify escrow observers
        await self.tx_service.dispute(user, payload.transaction_id, payload.reason)

        dispute = Dispute(
            transaction_id=payload.transaction_id,
            raised_by=user.id,
            reason=payload.reason,
            status="open",
        )
        return await self.dispute_repo.create(dispute)

    async def list_disputes(self, user: User) -> Sequence[Dispute]:
        return await self.dispute_repo.list_for_user(user.id)

    async def get_dispute(self, user: User, dispute_id: int) -> Dispute:
        dispute = await self.dispute_repo.get(dispute_id)
        if not dispute:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dispute not found")
        return dispute

    async def update_dispute(self, user: User, dispute_id: int, payload: DisputeUpdate) -> Dispute:
        dispute = await self.get_dispute(user, dispute_id)
        dispute.status = payload.status
        return await self.dispute_repo.update(dispute)


# Backward-compatible helper functions
def _get_service(db: AsyncSession) -> DisputeService:
    dispute_repo = SQLAlchemyDisputeRepository(db)
    txn_repo = SQLAlchemyTransactionRepository(db)
    event_repo = SQLAlchemyEscrowEventRepository(db)
    tx_service = TransactionService(txn_repo, event_repo)
    return DisputeService(dispute_repo, tx_service)


async def raise_dispute(db: AsyncSession, user: User, payload: DisputeCreate) -> Dispute:
    return await _get_service(db).raise_dispute(user, payload)


async def list_disputes(db: AsyncSession, user: User) -> Sequence[Dispute]:
    return await _get_service(db).list_disputes(user)


async def get_dispute(db: AsyncSession, user: User, dispute_id: int) -> Dispute:
    return await _get_service(db).get_dispute(user, dispute_id)


async def update_dispute(db: AsyncSession, user: User, dispute_id: int, payload: DisputeUpdate) -> Dispute:
    return await _get_service(db).update_dispute(user, dispute_id, payload)

