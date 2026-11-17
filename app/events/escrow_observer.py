from abc import ABC, abstractmethod
from typing import List, Optional, Any, Callable


class IEscrowObserver(ABC):
    """Observer interface for escrow lifecycle transitions (GoF Observer Pattern)."""

    @abstractmethod
    async def update(
        self,
        transaction_id: int,
        from_state: str,
        to_state: str,
        actor_id: Optional[int] = None,
        note: Optional[str] = None,
    ) -> None:
        """Invoked when an escrow transaction changes state."""
        pass


class AuditLogObserver(IEscrowObserver):
    """Writes an immutable record to the escrow_events table upon state transition."""

    def __init__(self, event_repo: Any):
        self.event_repo = event_repo

    async def update(
        self,
        transaction_id: int,
        from_state: str,
        to_state: str,
        actor_id: Optional[int] = None,
        note: Optional[str] = None,
    ) -> None:
        if hasattr(self.event_repo, "log_event"):
            await self.event_repo.log_event(
                transaction_id=transaction_id,
                from_state=from_state,
                to_state=to_state,
                actor_id=actor_id,
                note=note,
            )


class NotificationObserver(IEscrowObserver):
    """Sends / records notifications (SMS/push) to the transaction counterparties."""

    def __init__(self, notifier: Optional[Callable] = None):
        self.notifier = notifier
        self.notifications_sent: List[dict] = []

    async def update(
        self,
        transaction_id: int,
        from_state: str,
        to_state: str,
        actor_id: Optional[int] = None,
        note: Optional[str] = None,
    ) -> None:
        message = f"Escrow Tx #{transaction_id} transitioned from {from_state} to {to_state}"
        entry = {
            "transaction_id": transaction_id,
            "from_state": from_state,
            "to_state": to_state,
            "message": message,
            "actor_id": actor_id,
            "note": note,
        }
        self.notifications_sent.append(entry)
        if self.notifier:
            await self.notifier(entry)


class LotStatusObserver(IEscrowObserver):
    """Updates lot status (e.g. marking sold when funds are released)."""

    def __init__(self, lot_service_or_repo: Optional[Any] = None):
        self.lot_service_or_repo = lot_service_or_repo

    async def update(
        self,
        transaction_id: int,
        from_state: str,
        to_state: str,
        actor_id: Optional[int] = None,
        note: Optional[str] = None,
    ) -> None:
        if to_state == "FUNDS_RELEASED" and self.lot_service_or_repo:
            if hasattr(self.lot_service_or_repo, "mark_transaction_lots_sold"):
                await self.lot_service_or_repo.mark_transaction_lots_sold(transaction_id)


class EscrowSubject:
    """Subject in the GoF Observer Pattern managing escrow state change notifications."""

    def __init__(self):
        self._observers: List[IEscrowObserver] = []

    def attach(self, observer: IEscrowObserver) -> None:
        if observer not in self._observers:
            self._observers.append(observer)

    def detach(self, observer: IEscrowObserver) -> None:
        if observer in self._observers:
            self._observers.remove(observer)

    async def notify(
        self,
        transaction_id: int,
        from_state: str,
        to_state: str,
        actor_id: Optional[int] = None,
        note: Optional[str] = None,
    ) -> None:
        for observer in list(self._observers):
            await observer.update(
                transaction_id=transaction_id,
                from_state=from_state,
                to_state=to_state,
                actor_id=actor_id,
                note=note,
            )

