# Member 4: Bargaining Threads, Offers & Escrow State Machine

> **Assigned Team Member:** Member 4  
> **Core Role:** Financial Safety & State Machine Engineer  
> **Execution Priority:** **Step 4 (Executes Fourth)** — Consumes Member 3's matched bundles; Manages legal negotiation, escrow locking & dispute arbitration.

---

## 1. Domain Responsibility & Scope

Member 4 is responsible for the financial core and trust layer of the marketplace:
1. **Threaded Bilateral Bargaining (`app/models/offer.py`, `app/routers/offers.py`)**: Back-and-forth counter-offers between buyers and farmers with historical audit trails.
2. **Escrow Finite State Machine (`app/services/transaction_service.py`, `app/domain/states/`)**: Enforcing non-repudiation and strict state transitions:
   $$\text{CREATED} \to \text{DEPOSIT\_PAID} \to \text{DEPOSIT\_HELD} \to \text{IN\_TRANSIT} \to \text{INSPECTED} \to \text{FUNDS\_RELEASED}$$
3. **Immutable Audit Event Publishing (`app/events/escrow_events.py`)**: Observer-driven logging of every financial event to `escrow_events`.

---

## 2. Assigned Database Models (5 Tables)

Member 4 owns the following models in [`app/models/`](file:///Users/akashg/Desktop/Agriculture/Neolithic/app/models/):

| Model Name | Table Name | Purpose | Key Attributes & Foreign Keys |
| :--- | :--- | :--- | :--- |
| **`Offer`** | `offers` | Bargaining negotiation thread | `id` (PK), `demand_id` (FK $\to$ `buyer_demands`), `buyer_id`, `farmer_id`, `offered_price_paise`, `status` (`pending`, `countered`, `accepted`, `rejected`) |
| **`OfferLot`** | `offer_lots` | Association table | `id` (PK), `offer_id` (FK $\to$ `offers.id`), `lot_id` (FK $\to$ `lots.id`) |
| **`Transaction`** | `transactions` | Legally binding escrow order | `id` (PK), `offer_id` (FK $\to$ `offers.id`), `buyer_id`, `farmer_id`, `total_amount_paise`, `status` (`CREATED`, `DEPOSIT_HELD`, `IN_TRANSIT`, `INSPECTED`, `FUNDS_RELEASED`, `DISPUTED`) |
| **`EscrowEvent`** | `escrow_events` | Immutable audit log | `id` (PK), `transaction_id` (FK $\to$ `transactions.id`), `from_state`, `to_state`, `triggered_by_user_id`, `created_at` |
| **`Dispute`** | `disputes` | Conflict arbitration claim | `id` (PK), `transaction_id`, `raised_by_id`, `reason`, `status` (`open`, `investigating`, `resolved`) |

---

## 3. Assigned REST APIs (Endpoints & Contracts)

Member 4 owns [`app/routers/offers.py`](file:///Users/akashg/Desktop/Agriculture/Neolithic/app/routers/offers.py), [`app/routers/transactions.py`](file:///Users/akashg/Desktop/Agriculture/Neolithic/app/routers/transactions.py), and [`app/routers/disputes.py`](file:///Users/akashg/Desktop/Agriculture/Neolithic/app/routers/disputes.py):

| Method | Endpoint | Request Payload | Response Schema | Description |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/offers` | `{"lot_ids": [1, 2], "offered_price_paise": 230000}` | `OfferOut` | Buyer submits an offer on farmer lot(s) |
| `POST` | `/api/v1/offers/{id}/counter`| `{"counter_price_paise": 235000}` | `OfferOut` | Farmer or Buyer posts counter-offer |
| `POST` | `/api/v1/offers/{id}/accept` | *Empty* | `TransactionOut` | Accepts offer; spawns an Escrow Transaction in `CREATED` state |
| `POST` | `/api/v1/transactions/{id}/deposit` | `{"payment_proof": "pay_xyz"}` | `TransactionOut` | Buyer deposits funds; transitions to `DEPOSIT_HELD` |
| `POST` | `/api/v1/transactions/{id}/dispatch`| `{"vehicle_number": "MH15AB1234"}`| `TransactionOut` | Farmer dispatches cargo; transitions to `IN_TRANSIT` |
| `POST` | `/api/v1/transactions/{id}/inspect` | `{"quality_confirmed": true}` | `TransactionOut` | Buyer verifies quality; transitions to `INSPECTED` |
| `POST` | `/api/v1/transactions/{id}/release` | *Empty* | `TransactionOut` | Releases escrow payout to farmer (`FUNDS_RELEASED`) |
| `POST` | `/api/v1/disputes` | `{"transaction_id": 1, "reason": "decay"}` | `DisputeOut` | Halts fund release; transitions to `DISPUTED` |

---

## 4. GoF Design Patterns Implementation

### Pattern 1: State Pattern (Behavioral) — *Core Capstone USP*
- **Problem Solved**: Escrow transactions must obey strict business transitions. A buyer cannot release funds if the deposit was never paid. A farmer cannot dispatch goods if deposit isn't held. Out-of-order calls must throw `409 INVALID_TRANSITION`.
- **Implementation**:
  - `IEscrowState` interface with methods: `deposit()`, `dispatch()`, `inspect()`, `release()`, `dispute()`.
  - Concrete State Classes: `CreatedState`, `DepositHeldState`, `InTransitState`, `InspectedState`, `FundsReleasedState`, `DisputedState`.

```python
# app/domain/states/escrow_state.py
from abc import ABC, abstractmethod
from fastapi import HTTPException, status

class IEscrowState(ABC):
    @property
    @abstractmethod
    def name(self) -> str: pass

    def deposit(self, context) -> "IEscrowState":
        raise HTTPException(status_code=409, detail=f"Cannot deposit in state: {self.name}")

    def dispatch(self, context) -> "IEscrowState":
        raise HTTPException(status_code=409, detail=f"Cannot dispatch goods in state: {self.name}")

    def inspect(self, context) -> "IEscrowState":
        raise HTTPException(status_code=409, detail=f"Cannot inspect goods in state: {self.name}")

    def release(self, context) -> "IEscrowState":
        raise HTTPException(status_code=409, detail=f"Cannot release funds in state: {self.name}")

    def dispute(self, context) -> "IEscrowState":
        raise HTTPException(status_code=409, detail=f"Cannot dispute in state: {self.name}")


class CreatedState(IEscrowState):
    name = "CREATED"
    def deposit(self, context) -> IEscrowState:
        return DepositHeldState()

class DepositHeldState(IEscrowState):
    name = "DEPOSIT_HELD"
    def dispatch(self, context) -> IEscrowState:
        return InTransitState()

class InTransitState(IEscrowState):
    name = "IN_TRANSIT"
    def inspect(self, context) -> IEscrowState:
        return InspectedState()
    def dispute(self, context) -> IEscrowState:
        return DisputedState()

class InspectedState(IEscrowState):
    name = "INSPECTED"
    def release(self, context) -> IEscrowState:
        return FundsReleasedState()

class FundsReleasedState(IEscrowState):
    name = "FUNDS_RELEASED"

class DisputedState(IEscrowState):
    name = "DISPUTED"
```

### Pattern 2: Observer Pattern (Behavioral)
- **Problem Solved**: When a financial transition occurs, multiple decoupled side effects must run:
  1. Write an immutable audit log to `escrow_events`.
  2. Send notification (SMS) to the counterparty.
  3. Update farmer lot status to `sold`.
- **Implementation**:

```python
# app/events/escrow_observer.py
from abc import ABC, abstractmethod

class IEscrowObserver(ABC):
    @abstractmethod
    async def update(self, transaction_id: int, from_state: str, to_state: str): pass

class AuditLogObserver(IEscrowObserver):
    def __init__(self, event_repo):
        self.event_repo = event_repo

    async def update(self, transaction_id: int, from_state: str, to_state: str):
        await self.event_repo.log_event(transaction_id, from_state, to_state)

class EscrowSubject:
    def __init__(self):
        self._observers = []

    def attach(self, observer: IEscrowObserver):
        self._observers.append(observer)

    async def notify(self, transaction_id: int, from_state: str, to_state: str):
        for observer in self._observers:
            await observer.update(transaction_id, from_state, to_state)
```

---

## 5. SOLID Principles Proof Matrix (Member 4)

1. **Single Responsibility Principle (SRP)**:
   - `CreatedState` only knows what transitions are legal when an escrow order is created.
   - `AuditLogObserver` only handles writing to the audit database table.
2. **Open/Closed Principle (OCP)**:
   - Adding a new milestone (e.g. `PartialRefundState`) requires creating a new state class without modifying existing state classes.
3. **Liskov Substitution Principle (LSP)**:
   - Any state class substituting `IEscrowState` can be invoked by `TransactionService` without type errors or broken contracts.
4. **Interface Segregation Principle (ISP)**:
   - `IEscrowObserver` specifies only `update()`, allowing observers to be completely decoupled from the HTTP transport layer.
5. **Dependency Inversion Principle (DIP)**:
   - `TransactionService` depends on the abstraction `IEscrowState` and `IEscrowObserver`, not concrete notification scripts or raw database queries.

---

## 6. Pytest Automated Test Suite

Save in `tests/test_member_4_escrow_fsm.py`:

```python
import pytest
from fastapi import HTTPException
from app.domain.states.escrow_state import CreatedState, DepositHeldState, InTransitState, InspectedState, FundsReleasedState

def test_legal_escrow_lifecycle_happy_path():
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
    assert "Cannot release funds" in exc_info.value.detail

def test_illegal_dispatch_before_deposit_raises_409():
    state = CreatedState()
    with pytest.raises(HTTPException) as exc_info:
        state.dispatch(None)
    assert exc_info.value.status_code == 409
```

---

## 7. Faculty Viva Defense Guide (Member 4)

* **Faculty Q: "How does your State Pattern prevent race conditions or fraud in escrow payments?"**
  * *Answer:* *"In a naive design, status is just a string column in a database. If an API endpoint is called out of order (or maliciously), funds could be released before deposit or inspection. With the GoF State Pattern, the transaction's behavior is encapsulated in polymorphic state objects. In `CreatedState`, calling `release()` is not even an available operation—it throws a hard HTTP 409 Conflict. The transaction can only move along the mathematically verified state graph: $\text{CREATED} \to \text{DEPOSIT\_HELD} \to \text{IN\_TRANSIT} \to \text{INSPECTED} \to \text{FUNDS\_RELEASED}$."*

* **Faculty Q: "Why did you pair the State Pattern with the Observer Pattern?"**
  * *Answer:* *"To strictly adhere to Single Responsibility and Open/Closed principles. When a transaction changes state, several secondary operations must execute: creating an immutable audit log, notifying the farmer via SMS, and updating lot availability. If we wrote all of that inside the state transition method, it would violate SRP and create tight coupling. With the Observer pattern, the `EscrowSubject` simply notifies attached observers asynchronously."*

