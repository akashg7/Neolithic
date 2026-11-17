"""Transaction, EscrowEvent, and Dispute repository interfaces and SQLAlchemy implementations."""
from abc import abstractmethod
from typing import Optional, Sequence
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction, EscrowEvent
from app.models.dispute import Dispute
from app.repositories.base import IRepository, SQLAlchemyBaseRepository


class ITransactionRepository(IRepository[Transaction]):
    async def get(self, id: int) -> Optional[Transaction]:
        return await self.get_by_id(id)

    @abstractmethod
    async def get_with_events(self, transaction_id: int) -> Optional[Transaction]:
        """Get transaction with all related escrow events loaded."""
        pass

    @abstractmethod
    async def get_by_offer_id(self, offer_id: int) -> Optional[Transaction]:
        """Get transaction linked to a specific accepted offer."""
        pass

    @abstractmethod
    async def list_for_user(self, user_id: int) -> Sequence[Transaction]:
        """List transactions for a buyer or farmer."""
        pass


class IEscrowEventRepository(IRepository[EscrowEvent]):
    async def get(self, id: int) -> Optional[EscrowEvent]:
        return await self.get_by_id(id)

    @abstractmethod
    async def list_for_transaction(self, transaction_id: int) -> Sequence[EscrowEvent]:
        """List all events for a transaction ordered chronologically."""
        pass

    @abstractmethod
    async def log_event(
        self,
        transaction_id: int,
        from_state: Optional[str],
        to_state: str,
        actor_id: Optional[int] = None,
        note: Optional[str] = None,
    ) -> EscrowEvent:
        """Create and persist an immutable escrow transition event."""
        pass


class IDisputeRepository(IRepository[Dispute]):
    async def get(self, id: int) -> Optional[Dispute]:
        return await self.get_by_id(id)

    @abstractmethod
    async def list_for_user(self, user_id: int) -> Sequence[Dispute]:
        """List disputes raised by or affecting a user."""
        pass

    @abstractmethod
    async def list_for_transaction(self, transaction_id: int) -> Sequence[Dispute]:
        """List all disputes for a transaction."""
        pass


class SQLAlchemyTransactionRepository(SQLAlchemyBaseRepository[Transaction], ITransactionRepository):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Transaction)

    async def get(self, id: int) -> Optional[Transaction]:
        return await self.get_by_id(id)

    async def get_with_events(self, transaction_id: int) -> Optional[Transaction]:
        query = (
            select(Transaction)
            .options(selectinload(Transaction.events))
            .where(Transaction.id == transaction_id)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_offer_id(self, offer_id: int) -> Optional[Transaction]:
        query = select(Transaction).where(Transaction.offer_id == offer_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: int) -> Sequence[Transaction]:
        query = (
            select(Transaction)
            .where((Transaction.buyer_id == user_id) | (Transaction.farmer_id == user_id))
            .order_by(Transaction.created_at.desc())
        )
        result = await self.session.execute(query)
        return result.scalars().all()


class SQLAlchemyEscrowEventRepository(SQLAlchemyBaseRepository[EscrowEvent], IEscrowEventRepository):
    def __init__(self, session: AsyncSession):
        super().__init__(session, EscrowEvent)

    async def get(self, id: int) -> Optional[EscrowEvent]:
        return await self.get_by_id(id)

    async def list_for_transaction(self, transaction_id: int) -> Sequence[EscrowEvent]:
        query = (
            select(EscrowEvent)
            .where(EscrowEvent.transaction_id == transaction_id)
            .order_by(EscrowEvent.created_at.asc())
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def log_event(
        self,
        transaction_id: int,
        from_state: Optional[str],
        to_state: str,
        actor_id: Optional[int] = None,
        note: Optional[str] = None,
    ) -> EscrowEvent:
        event = EscrowEvent(
            transaction_id=transaction_id,
            status_from=from_state,
            status_to=to_state,
            actor_id=actor_id or 1,
            note=note,
        )
        self.session.add(event)
        await self.session.flush()
        return event


class SQLAlchemyDisputeRepository(SQLAlchemyBaseRepository[Dispute], IDisputeRepository):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Dispute)

    async def get(self, id: int) -> Optional[Dispute]:
        return await self.get_by_id(id)

    async def list_for_user(self, user_id: int) -> Sequence[Dispute]:
        query = select(Dispute).where(Dispute.raised_by == user_id).order_by(Dispute.created_at.desc())
        result = await self.session.execute(query)
        return result.scalars().all()

    async def list_for_transaction(self, transaction_id: int) -> Sequence[Dispute]:
        query = select(Dispute).where(Dispute.transaction_id == transaction_id).order_by(Dispute.created_at.desc())
        result = await self.session.execute(query)
        return result.scalars().all()
