"""Member 4 Automated Test Suite: State Pattern, Observer Pattern, Offers & Escrow FSM.

Validates:
1. GoF State Pattern (IEscrowState polymorphic transitions & 409 HTTPExceptions on illegal jumps)
2. GoF Observer Pattern (EscrowSubject & AuditLogObserver decoupling)
3. Bilateral bargaining thread & counter-offer round capping (max 3 rounds)
4. Escrow financial order lifecycle: CREATED -> DEPOSIT_HELD -> IN_TRANSIT -> INSPECTED -> FUNDS_RELEASED
5. Dispute arbitration halting fund release -> DISPUTED
6. Full REST API endpoints with authentication and dependency injection.
"""
from datetime import datetime, timezone
from typing import Optional, Sequence, List, Dict, Any
import pytest
import pytest_asyncio
from fastapi import FastAPI, HTTPException, status
from httpx import ASGITransport, AsyncClient

from app.dependencies.auth import get_current_user
from app.database import get_db
from app.domain.states.escrow_state import (
    IEscrowState,
    CreatedState,
    DepositHeldState,
    InTransitState,
    InspectedState,
    FundsReleasedState,
    DisputedState,
    get_state,
)
from app.events.escrow_observer import (
    IEscrowObserver,
    EscrowSubject,
    AuditLogObserver,
    NotificationObserver,
)
from app.models.user import User
from app.models.offer import Offer, OfferLot
from app.models.transaction import Transaction, EscrowEvent
from app.models.dispute import Dispute
from app.repositories.offer_repository import IOfferRepository
from app.repositories.transaction_repository import (
    ITransactionRepository,
    IEscrowEventRepository,
    IDisputeRepository,
)
from app.schemas.offer import OfferCreate, OfferCounterReq
from app.schemas.transaction import DepositReq, DispatchReq, InspectReq, ReleaseReq, FSMTransitionReq
from app.schemas.dispute import DisputeCreate, DisputeUpdate
from app.services.offer_service import OfferService
from app.services.transaction_service import TransactionService
from app.services.dispute_service import DisputeService
from app.routers import offers as offers_router
from app.routers import transactions as transactions_router
from app.routers import disputes as disputes_router
from app.dependencies.escrow import (
    get_offer_service,
    get_transaction_service,
    get_dispute_service,
)


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Override conftest's Postgres create/drop: test suite uses test doubles / in-memory repos."""
    yield


# ── Test Doubles / In-Memory Repositories ───────────────────────────────────

class InMemoryBaseRepo:
    def __init__(self):
        self._items: Dict[int, Any] = {}
        self._next_id = 1

    async def get_by_id(self, id: int):
        return self._items.get(id)

    async def get(self, id: int):
        return self._items.get(id)

    async def list(self, skip: int = 0, limit: int = 100):
        return list(self._items.values())[skip : skip + limit]

    async def create(self, entity):
        if not getattr(entity, "id", None):
            entity.id = self._next_id
            self._next_id += 1
        entity.created_at = getattr(entity, "created_at", None) or datetime.now(timezone.utc)
        self._items[entity.id] = entity
        return entity

    async def update(self, entity):
        self._items[entity.id] = entity
        return entity

    async def delete(self, id: int) -> bool:
        return self._items.pop(id, None) is not None

    async def commit(self) -> None:
        pass


class InMemoryOfferRepository(InMemoryBaseRepo, IOfferRepository):
    def __init__(self):
        super().__init__()
        self._lots: List[OfferLot] = []

    async def list_for_user(self, user_id: int, role: str) -> Sequence[Offer]:
        results = []
        for o in self._items.values():
            if role.upper() == "BUYER" and o.buyer_id == user_id:
                results.append(o)
            elif role.upper() != "BUYER" and o.farmer_id == user_id:
                results.append(o)
        return results

    async def get_with_lots(self, offer_id: int) -> Optional[Offer]:
        offer = self._items.get(offer_id)
        if offer:
            offer.lots = [l for l in self._lots if l.offer_id == offer_id]
        return offer

    async def get_offer_thread(self, offer_id: int) -> Sequence[Offer]:
        offer = self._items.get(offer_id)
        if not offer:
            return []
        thread = [offer]
        curr = offer
        while curr.parent_offer_id:
            parent = self._items.get(curr.parent_offer_id)
            if not parent:
                break
            thread.append(parent)
            curr = parent
        thread.reverse()
        return thread

    async def add_offer_lot(self, offer_lot: OfferLot) -> OfferLot:
        self._lots.append(offer_lot)
        return offer_lot


class InMemoryTransactionRepository(InMemoryBaseRepo, ITransactionRepository):
    async def create(self, entity: Transaction) -> Transaction:
        res = await super().create(entity)
        if not hasattr(res, "events") or res.events is None:
            res.events = []
        return res

    async def get_with_events(self, transaction_id: int) -> Optional[Transaction]:
        return self._items.get(transaction_id)

    async def get_by_offer_id(self, offer_id: int) -> Optional[Transaction]:
        for txn in self._items.values():
            if txn.offer_id == offer_id:
                return txn
        return None

    async def list_for_user(self, user_id: int) -> Sequence[Transaction]:
        return [
            t for t in self._items.values()
            if t.buyer_id == user_id or t.farmer_id == user_id
        ]


class InMemoryEscrowEventRepository(InMemoryBaseRepo, IEscrowEventRepository):
    async def list_for_transaction(self, transaction_id: int) -> Sequence[EscrowEvent]:
        return [e for e in self._items.values() if e.transaction_id == transaction_id]

    async def log_event(
        self,
        transaction_id: int,
        from_state: Optional[str],
        to_state: str,
        actor_id: Optional[int] = None,
        note: Optional[str] = None,
    ) -> EscrowEvent:
        event = EscrowEvent(
            id=self._next_id,
            transaction_id=transaction_id,
            status_from=from_state,
            status_to=to_state,
            actor_id=actor_id or 1,
            note=note,
            created_at=datetime.now(timezone.utc),
        )
        self._next_id += 1
        self._items[event.id] = event
        return event


class InMemoryDisputeRepository(InMemoryBaseRepo, IDisputeRepository):
    async def list_for_user(self, user_id: int) -> Sequence[Dispute]:
        return [d for d in self._items.values() if d.raised_by == user_id]

    async def list_for_transaction(self, transaction_id: int) -> Sequence[Dispute]:
        return [d for d in self._items.values() if d.transaction_id == transaction_id]


# ── Unit Tests: GoF State Pattern ──────────────────────────────────────────

def test_legal_escrow_lifecycle_happy_path():
    """Mathematical verification: CREATED -> DEPOSIT_HELD -> IN_TRANSIT -> INSPECTED -> FUNDS_RELEASED"""
    state = CreatedState()
    assert state.name == "CREATED"

    state = state.deposit(None)
    assert state.name == "DEPOSIT_HELD"

    state = state.dispatch(None)
    assert state.name == "IN_TRANSIT"

    state = state.inspect(None)
    assert state.name == "INSPECTED"

    state = state.release(None)
    assert state.name == "FUNDS_RELEASED"


def test_illegal_jump_from_created_to_release_raises_409():
    state = CreatedState()
    with pytest.raises(HTTPException) as exc_info:
        state.release(None)
    assert exc_info.value.status_code == 409
    assert "Cannot release funds in state: CREATED" in exc_info.value.detail


def test_illegal_dispatch_before_deposit_raises_409():
    state = CreatedState()
    with pytest.raises(HTTPException) as exc_info:
        state.dispatch(None)
    assert exc_info.value.status_code == 409
    assert "Cannot dispatch goods in state: CREATED" in exc_info.value.detail


def test_illegal_inspect_before_dispatch_raises_409():
    state = DepositHeldState()
    with pytest.raises(HTTPException) as exc_info:
        state.inspect(None)
    assert exc_info.value.status_code == 409
    assert "Cannot inspect goods in state: DEPOSIT_HELD" in exc_info.value.detail


def test_illegal_release_before_inspection_raises_409():
    state = InTransitState()
    with pytest.raises(HTTPException) as exc_info:
        state.release(None)
    assert exc_info.value.status_code == 409
    assert "Cannot release funds in state: IN_TRANSIT" in exc_info.value.detail


def test_illegal_deposit_when_already_held_raises_409():
    state = DepositHeldState()
    with pytest.raises(HTTPException) as exc_info:
        state.deposit(None)
    assert exc_info.value.status_code == 409
    assert "Cannot deposit in state: DEPOSIT_HELD" in exc_info.value.detail


def test_terminal_state_funds_released_rejects_all_further_transitions():
    state = FundsReleasedState()
    assert state.name == "FUNDS_RELEASED"
    for method in [state.deposit, state.dispatch, state.inspect, state.release, state.dispute]:
        with pytest.raises(HTTPException) as exc:
            method(None)
        assert exc.value.status_code == 409


def test_dispute_branches_from_in_transit_and_inspected():
    # In transit dispute (e.g. lost in transit or accident)
    state = InTransitState()
    disputed = state.dispute("Goods delayed past agreed window")
    assert disputed.name == "DISPUTED"

    # Inspected dispute (e.g. decayed or spoiled lot)
    state2 = InspectedState()
    disputed2 = state2.dispute("Quality mismatch: Grade C instead of Grade A")
    assert disputed2.name == "DISPUTED"

    # Disputed state allows release upon arbitration resolution
    resolved = disputed2.release(None)
    assert resolved.name == "FUNDS_RELEASED"


def test_state_factory_and_apply_action():
    state = get_state("CREATED")
    assert isinstance(state, CreatedState)

    state = state.apply_action("DEPOSIT_PAID")
    assert isinstance(state, DepositHeldState)

    state = state.apply_action("DISPATCHED")
    assert isinstance(state, InTransitState)

    state = state.apply_action("INSPECTED_OK")
    assert isinstance(state, InspectedState)

    state = state.apply_action("FUNDS_TRANSFER")
    assert isinstance(state, FundsReleasedState)

    with pytest.raises(HTTPException) as exc:
        get_state("INVALID_NONEXISTENT_STATE")
    assert exc.value.status_code == 400


# ── Unit Tests: GoF Observer Pattern ───────────────────────────────────────

@pytest.mark.asyncio
async def test_escrow_subject_and_audit_observer_integration():
    event_repo = InMemoryEscrowEventRepository()
    audit_observer = AuditLogObserver(event_repo)
    notif_observer = NotificationObserver()

    subject = EscrowSubject()
    subject.attach(audit_observer)
    subject.attach(notif_observer)

    await subject.notify(
        transaction_id=101,
        from_state="CREATED",
        to_state="DEPOSIT_HELD",
        actor_id=5,
        note="UPI deposit confirmed",
    )

    # 1. Audit logger wrote to repository
    events = await event_repo.list_for_transaction(101)
    assert len(events) == 1
    assert events[0].status_from == "CREATED"
    assert events[0].status_to == "DEPOSIT_HELD"
    assert events[0].actor_id == 5
    assert events[0].note == "UPI deposit confirmed"

    # 2. Notification observer dispatched message
    assert len(notif_observer.notifications_sent) == 1
    assert "DEPOSIT_HELD" in notif_observer.notifications_sent[0]["message"]

    # 3. Detaching works cleanly
    subject.detach(notif_observer)
    await subject.notify(transaction_id=101, from_state="DEPOSIT_HELD", to_state="IN_TRANSIT")
    assert len(notif_observer.notifications_sent) == 1  # Unchanged
    assert len(await event_repo.list_for_transaction(101)) == 2  # Audit still logged


# ── Service Layer Tests: Offers & Escrow FSM ────────────────────────────────

@pytest.mark.asyncio
async def test_offer_counter_bargaining_max_rounds():
    offer_repo = InMemoryOfferRepository()
    service = OfferService(offer_repo)

    buyer = User(id=1, phone="9876543210", role="BUYER")
    farmer = User(id=2, phone="9876543211", role="FARMER")

    # Round 1: Buyer creates offer
    create_payload = OfferCreate(
        lot_ids=[1, 2],
        qty_kg=1000,
        price_paise_per_qtl=230000,
    )
    r1 = await service.create_offer(buyer, create_payload)
    assert r1["round"] == 1
    assert r1["status"] == "OPEN"
    assert r1["initiator"] == "BUYER"
    offer_id_1 = int(r1["id"])

    # Round 2: Farmer counters
    r2 = await service.counter_offer(farmer, offer_id_1, OfferCounterReq(price_paise_per_qtl=240000))
    assert r2["round"] == 2
    assert r2["status"] == "OPEN"
    assert r2["initiator"] == "FARMER"
    assert r2["parent_offer_id"] == str(offer_id_1)
    offer_id_2 = int(r2["id"])

    # Original offer is marked COUNTERED
    original = await offer_repo.get(offer_id_1)
    assert original.status == "COUNTERED"

    # Round 3: Buyer counters again
    r3 = await service.counter_offer(buyer, offer_id_2, OfferCounterReq(price_paise_per_qtl=235000))
    assert r3["round"] == 3
    offer_id_3 = int(r3["id"])

    # Round 4 attempt: Must raise 409 MAX_ROUNDS
    with pytest.raises(HTTPException) as exc:
        await service.counter_offer(farmer, offer_id_3, OfferCounterReq(price_paise_per_qtl=238000))
    assert exc.value.status_code == 409
    assert exc.value.detail["error"]["code"] == "MAX_ROUNDS"


@pytest.mark.asyncio
async def test_offer_accept_spawns_escrow_transaction_in_created_state():
    offer_repo = InMemoryOfferRepository()
    txn_repo = InMemoryTransactionRepository()
    event_repo = InMemoryEscrowEventRepository()

    tx_service = TransactionService(txn_repo, event_repo, offer_repo)
    offer_service = OfferService(offer_repo, tx_service)

    buyer = User(id=1, phone="9876543210", role="BUYER")
    farmer = User(id=2, phone="9876543211", role="FARMER")

    offer_data = await offer_service.create_offer(
        buyer,
        OfferCreate(lot_ids=[1], qty_kg=2000, price_paise_per_qtl=250000),
    )
    offer_id = int(offer_data["id"])

    # Farmer accepts the offer
    txn = await offer_service.accept_offer(farmer, offer_id)

    assert txn.offer_id == offer_id
    assert txn.status == "CREATED"
    # 2000 kg @ 250000 paise/qtl (100kg) = 20 qtl * 250000 = 5,000,000 paise
    assert txn.amount_paise == 5000000

    # Escrow events audit log has creation entry
    events = await event_repo.list_for_transaction(txn.id)
    assert len(events) == 1
    assert events[0].status_to == "CREATED"


@pytest.mark.asyncio
async def test_dispute_halts_escrow_lifecycle():
    offer_repo = InMemoryOfferRepository()
    txn_repo = InMemoryTransactionRepository()
    event_repo = InMemoryEscrowEventRepository()
    dispute_repo = InMemoryDisputeRepository()

    tx_service = TransactionService(txn_repo, event_repo, offer_repo)
    dispute_service = DisputeService(dispute_repo, tx_service)

    buyer = User(id=10, phone="9876543210", role="BUYER")
    farmer = User(id=20, phone="9876543211", role="FARMER")

    # Seed transaction in IN_TRANSIT
    txn = Transaction(
        id=55,
        offer_id=99,
        buyer_id=10,
        farmer_id=20,
        amount_paise=100000,
        status="IN_TRANSIT",
    )
    await txn_repo.create(txn)

    # Buyer raises dispute
    d = await dispute_service.raise_dispute(
        buyer,
        DisputeCreate(transaction_id=55, reason="decay and bad packaging"),
    )
    assert d.transaction_id == 55
    assert d.reason == "decay and bad packaging"
    assert d.status == "open"

    # Transaction moved to DISPUTED
    updated_txn = await tx_service.get_transaction(buyer, 55)
    assert updated_txn.status == "DISPUTED"

    # Further dispatch or inspect is now blocked (409)
    with pytest.raises(HTTPException) as exc:
        await tx_service.dispatch(farmer, 55, DispatchReq())
    assert exc.value.status_code == 409


# ── Full HTTP Integration Tests ─────────────────────────────────────────────

@pytest_asyncio.fixture
async def api_client():
    offer_repo = InMemoryOfferRepository()
    txn_repo = InMemoryTransactionRepository()
    event_repo = InMemoryEscrowEventRepository()
    dispute_repo = InMemoryDisputeRepository()

    tx_service = TransactionService(txn_repo, event_repo, offer_repo)
    off_service = OfferService(offer_repo, tx_service)
    disp_service = DisputeService(dispute_repo, tx_service)

    buyer_user = User(id=1, phone="9000000001", role="BUYER")
    farmer_user = User(id=2, phone="9000000002", role="FARMER")

    app = FastAPI()
    app.include_router(offers_router.router, prefix="/api/v1/offers")
    app.include_router(transactions_router.router, prefix="/api/v1/transactions")
    app.include_router(disputes_router.router, prefix="/api/v1/disputes")

    # Dependency overrides
    app.dependency_overrides[get_current_user] = lambda: buyer_user
    app.dependency_overrides[get_offer_service] = lambda: off_service
    app.dependency_overrides[get_transaction_service] = lambda: tx_service
    app.dependency_overrides[get_dispute_service] = lambda: disp_service

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, tx_service, off_service, buyer_user, farmer_user


@pytest.mark.asyncio
async def test_full_escrow_api_pipeline_and_invalid_state_transitions(api_client):
    client, tx_service, off_service, buyer, farmer = api_client

    # 1. POST /api/v1/offers — Buyer creates offer
    res = await client.post(
        "/api/v1/offers",
        json={"lot_ids": [10, 20], "offered_price_paise": 230000, "qty_kg": 1000},
    )
    assert res.status_code == 201
    offer_data = res.json()
    assert offer_data["status"] == "OPEN"
    offer_id = int(offer_data["id"])

    # 2. POST /api/v1/offers/{id}/counter — the FARMER counters (a party may
    #    not accept their own offer, so the counter must come from the other side)
    overrides = client._transport.app.dependency_overrides
    overrides[get_current_user] = lambda: farmer
    res = await client.post(
        f"/api/v1/offers/{offer_id}/counter",
        json={"counter_price_paise": 235000},
    )
    overrides[get_current_user] = lambda: buyer
    assert res.status_code == 200
    counter_data = res.json()
    assert counter_data["round"] == 2
    counter_id = int(counter_data["id"])

    # 3. POST /api/v1/offers/{id}/accept — Accepts offer; spawns Escrow Transaction
    res = await client.post(f"/api/v1/offers/{counter_id}/accept")
    assert res.status_code == 200
    tx_data = res.json()
    assert tx_data["status"] == "CREATED"
    tx_id = int(tx_data["id"])

    # 4. Out-of-order jump check: Buyer tries to RELEASE directly from CREATED -> 409
    res = await client.post(f"/api/v1/transactions/{tx_id}/release")
    assert res.status_code == 409
    assert "Cannot release funds in state: CREATED" in res.json()["detail"]

    # 5. Out-of-order jump check: Farmer tries to DISPATCH before deposit -> 409
    res = await client.post(f"/api/v1/transactions/{tx_id}/dispatch", json={"vehicle_number": "MH15AB1234"})
    assert res.status_code == 409
    assert "Cannot dispatch goods in state: CREATED" in res.json()["detail"]

    # 6. POST /api/v1/transactions/{id}/deposit — Buyer deposits funds
    res = await client.post(f"/api/v1/transactions/{tx_id}/deposit", json={"payment_proof": "pay_xyz"})
    assert res.status_code == 200
    assert res.json()["status"] == "DEPOSIT_HELD"

    # 7. POST /api/v1/transactions/{id}/dispatch — Farmer dispatches cargo
    res = await client.post(f"/api/v1/transactions/{tx_id}/dispatch", json={"vehicle_number": "MH15AB1234"})
    assert res.status_code == 200
    assert res.json()["status"] == "IN_TRANSIT"

    # 8. POST /api/v1/transactions/{id}/inspect — Buyer verifies cargo
    res = await client.post(f"/api/v1/transactions/{tx_id}/inspect", json={"quality_confirmed": True})
    assert res.status_code == 200
    assert res.json()["status"] == "INSPECTED"

    # 9. POST /api/v1/transactions/{id}/release — Funds released to farmer
    res = await client.post(f"/api/v1/transactions/{tx_id}/release")
    assert res.status_code == 200
    assert res.json()["status"] == "FUNDS_RELEASED"

    # 10. Check GET /api/v1/transactions/{id}/events — Timeline is append-only
    res = await client.get(f"/api/v1/transactions/{tx_id}/events")
    assert res.status_code == 200
    events = res.json()
    assert len(events) >= 5
    states_sequence = [e["status_to"] for e in events]
    assert "CREATED" in states_sequence
    assert "DEPOSIT_HELD" in states_sequence
    assert "IN_TRANSIT" in states_sequence
    assert "INSPECTED" in states_sequence
    assert "FUNDS_RELEASED" in states_sequence


@pytest.mark.asyncio
async def test_dispute_api_flow(api_client):
    client, tx_service, off_service, buyer, farmer = api_client

    # Create transaction and move to IN_TRANSIT
    txn = Transaction(
        id=77,
        offer_id=12,
        buyer_id=buyer.id,
        farmer_id=farmer.id,
        amount_paise=400000,
        status="IN_TRANSIT",
    )
    await tx_service.txn_repo.create(txn)

    # POST /api/v1/disputes — Buyer raises dispute
    res = await client.post(
        "/api/v1/disputes",
        json={"transaction_id": 77, "reason": "decay"},
    )
    assert res.status_code == 201
    dispute_data = res.json()
    assert dispute_data["transaction_id"] == 77
    assert dispute_data["reason"] == "decay"
    assert dispute_data["status"] == "open"
    dispute_id = dispute_data["id"]

    # Transaction is now DISPUTED
    res = await client.get(f"/api/v1/transactions/77")
    assert res.status_code == 200
    assert res.json()["status"] == "DISPUTED"

    # PATCH /api/v1/disputes/{id} — Update dispute to investigating
    res = await client.patch(
        f"/api/v1/disputes/{dispute_id}",
        json={"status": "investigating"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "investigating"
