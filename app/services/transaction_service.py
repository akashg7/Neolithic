"""Transaction & Escrow State Machine Service.

Implements the GoF State Pattern (IEscrowState) and GoF Observer Pattern (EscrowSubject).
"""
from typing import Optional, Sequence, List, Any
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.user import User
from app.models.offer import Offer
from app.models.transaction import Transaction, EscrowEvent
from app.domain.states.escrow_state import get_state, IEscrowState
from app.events.escrow_observer import EscrowSubject, AuditLogObserver, NotificationObserver
from app.repositories.transaction_repository import (
    ITransactionRepository,
    SQLAlchemyTransactionRepository,
    IEscrowEventRepository,
    SQLAlchemyEscrowEventRepository,
)
from app.repositories.offer_repository import (
    IOfferRepository,
    SQLAlchemyOfferRepository,
)
from app.schemas.transaction import (
    FSMTransitionReq,
    DepositReq,
    DispatchReq,
    InspectReq,
    ReleaseReq,
)


class TransactionService:
    def __init__(
        self,
        transaction_repo: ITransactionRepository,
        event_repo: IEscrowEventRepository,
        offer_repo: Optional[IOfferRepository] = None,
        subject: Optional[EscrowSubject] = None,
    ):
        self.txn_repo = transaction_repo
        self.event_repo = event_repo
        self.offer_repo = offer_repo
        self.subject = subject or EscrowSubject()
        # Attach default audit logger to subject
        self.subject.attach(AuditLogObserver(self.event_repo))

    async def get_transaction(self, user: User, transaction_id: int) -> Transaction:
        txn = await self.txn_repo.get_with_events(transaction_id)
        if not txn:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
        if not isinstance(self.txn_repo, SQLAlchemyTransactionRepository):
            events = await self.event_repo.list_for_transaction(txn.id)
            txn.events = events
        return txn

    async def create_transaction_for_offer(
        self,
        user: User,
        offer: Offer,
    ) -> Transaction:
        """Spawn an escrow transaction in CREATED state when an offer is accepted."""
        # Check if transaction already exists for this offer
        existing = await self.txn_repo.get_by_offer_id(offer.id)
        if existing:
            return existing

        # Total amount in paise: if qty_kg and price_paise_per_qtl, standard calculation
        # price_paise_per_qtl is per 100kg (quintal)
        if offer.qty_kg and offer.price_paise_per_qtl:
            amount_paise = (offer.price_paise_per_qtl * offer.qty_kg) // 100
        else:
            amount_paise = offer.price_paise_per_qtl or 200000

        txn = Transaction(
            offer_id=offer.id,
            buyer_id=offer.buyer_id,
            farmer_id=offer.farmer_id,
            amount_paise=amount_paise,
            status="CREATED",
        )
        created_txn = await self.txn_repo.create(txn)

        # Notify observers of initial creation
        await self.subject.notify(
            transaction_id=created_txn.id,
            from_state=None,
            to_state="CREATED",
            actor_id=user.id,
            note="Escrow transaction created from accepted offer",
        )

        return await self.get_transaction(user, created_txn.id)

    async def deposit(
        self,
        user: User,
        transaction_id: int,
        payload: Optional[DepositReq] = None,
    ) -> Transaction:
        """Buyer deposits funds into escrow; transitions CREATED -> DEPOSIT_HELD."""
        txn = await self.get_transaction(user, transaction_id)
        curr_state = get_state(txn.status)
        next_state = curr_state.deposit(payload)

        from_state = txn.status
        to_state = next_state.name
        txn.status = to_state
        await self.txn_repo.update(txn)

        note = payload.note if payload and payload.note else "Buyer deposited funds to escrow"
        await self.subject.notify(
            transaction_id=txn.id,
            from_state=from_state,
            to_state=to_state,
            actor_id=user.id,
            note=note,
        )
        return await self.get_transaction(user, txn.id)

    async def dispatch(
        self,
        user: User,
        transaction_id: int,
        payload: Optional[DispatchReq] = None,
    ) -> Transaction:
        """Farmer dispatches goods; transitions DEPOSIT_HELD -> IN_TRANSIT."""
        txn = await self.get_transaction(user, transaction_id)
        curr_state = get_state(txn.status)
        next_state = curr_state.dispatch(payload)

        from_state = txn.status
        to_state = next_state.name
        txn.status = to_state
        await self.txn_repo.update(txn)

        note = payload.note if payload and payload.note else (
            f"Farmer dispatched cargo (Vehicle: {payload.vehicle_number})" if payload and payload.vehicle_number else "Cargo dispatched"
        )
        await self.subject.notify(
            transaction_id=txn.id,
            from_state=from_state,
            to_state=to_state,
            actor_id=user.id,
            note=note,
        )
        return await self.get_transaction(user, txn.id)

    async def inspect(
        self,
        user: User,
        transaction_id: int,
        payload: Optional[InspectReq] = None,
    ) -> Transaction:
        """Buyer verifies cargo quality; transitions IN_TRANSIT -> INSPECTED."""
        txn = await self.get_transaction(user, transaction_id)
        curr_state = get_state(txn.status)
        next_state = curr_state.inspect(payload)

        from_state = txn.status
        to_state = next_state.name
        txn.status = to_state
        await self.txn_repo.update(txn)

        note = payload.note if payload and payload.note else "Buyer verified cargo quality"
        await self.subject.notify(
            transaction_id=txn.id,
            from_state=from_state,
            to_state=to_state,
            actor_id=user.id,
            note=note,
        )
        return await self.get_transaction(user, txn.id)

    async def release(
        self,
        user: User,
        transaction_id: int,
        payload: Optional[ReleaseReq] = None,
    ) -> Transaction:
        """Releases escrow funds to farmer; transitions INSPECTED -> FUNDS_RELEASED."""
        txn = await self.get_transaction(user, transaction_id)
        curr_state = get_state(txn.status)
        next_state = curr_state.release(payload)

        from_state = txn.status
        to_state = next_state.name
        txn.status = to_state
        await self.txn_repo.update(txn)

        note = payload.note if payload and payload.note else "Escrow funds released to farmer payout"
        await self.subject.notify(
            transaction_id=txn.id,
            from_state=from_state,
            to_state=to_state,
            actor_id=user.id,
            note=note,
        )
        return await self.get_transaction(user, txn.id)

    async def dispute(
        self,
        user: User,
        transaction_id: int,
        reason: str,
    ) -> Transaction:
        """Halts release and places transaction into DISPUTED state."""
        txn = await self.get_transaction(user, transaction_id)
        curr_state = get_state(txn.status)
        next_state = curr_state.dispute(reason)

        from_state = txn.status
        to_state = next_state.name
        txn.status = to_state
        await self.txn_repo.update(txn)

        await self.subject.notify(
            transaction_id=txn.id,
            from_state=from_state,
            to_state=to_state,
            actor_id=user.id,
            note=f"Dispute raised: {reason}",
        )
        return await self.get_transaction(user, txn.id)

    async def transition_state(
        self,
        user: User,
        transaction_id: int,
        payload: FSMTransitionReq,
    ) -> Transaction:
        """Generic state machine transition endpoint using State Pattern."""
        txn = await self.get_transaction(user, transaction_id)
        curr_state = get_state(txn.status)
        next_state = curr_state.apply_action(payload.action)

        from_state = txn.status
        to_state = next_state.name
        txn.status = to_state
        await self.txn_repo.update(txn)

        await self.subject.notify(
            transaction_id=txn.id,
            from_state=from_state,
            to_state=to_state,
            actor_id=user.id,
            note=payload.note,
        )
        return await self.get_transaction(user, txn.id)


# Backward-compatible helper functions delegating to TransactionService
def _get_service(db: AsyncSession) -> TransactionService:
    txn_repo = SQLAlchemyTransactionRepository(db)
    event_repo = SQLAlchemyEscrowEventRepository(db)
    offer_repo = SQLAlchemyOfferRepository(db)
    return TransactionService(txn_repo, event_repo, offer_repo)


async def get_transaction(db: AsyncSession, user: User, transaction_id: int):
    return await _get_service(db).get_transaction(user, transaction_id)


async def transition_state(db: AsyncSession, user: User, transaction_id: int, payload: FSMTransitionReq):
    return await _get_service(db).transition_state(user, transaction_id, payload)


async def deposit(db: AsyncSession, user: User, transaction_id: int, payload: Optional[DepositReq] = None):
    return await _get_service(db).deposit(user, transaction_id, payload)


async def dispatch(db: AsyncSession, user: User, transaction_id: int, payload: Optional[DispatchReq] = None):
    return await _get_service(db).dispatch(user, transaction_id, payload)


async def inspect(db: AsyncSession, user: User, transaction_id: int, payload: Optional[InspectReq] = None):
    return await _get_service(db).inspect(user, transaction_id, payload)


async def release(db: AsyncSession, user: User, transaction_id: int, payload: Optional[ReleaseReq] = None):
    return await _get_service(db).release(user, transaction_id, payload)


async def dispute(db: AsyncSession, user: User, transaction_id: int, reason: str):
    return await _get_service(db).dispute(user, transaction_id, reason)
