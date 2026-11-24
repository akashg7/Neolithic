# Member 1: User Identity, Roles & Generic Repository Architecture

> **Assigned Team Member:** Member 1  
> **Core Role:** Foundation Architect & Security Engineer  
> **Execution Priority:** **Step 1 (First to Execute)** — All other 4 members build upon Member 1's code.

---

## 1. Domain Responsibility & Scope

Member 1 is responsible for the bedrock foundation of the entire system:
1. **Generic Repository Pattern (`app/repositories/base.py`)**: Abstracting database access into a reusable, type-safe generic interface (`IRepository[T]`, `SQLAlchemyBaseRepository[T]`). Members 2, 3, 4, and 5 will inherit and use this.
2. **User Identity & Role Polymorphism (`app/models/user.py`, `app/models/fpo.py`, `app/models/otp.py`)**: Supporting distinct actors—`Farmer`, `Buyer`, and `FPO`—with role-based access control and JWT authentication.
3. **Factory Method Pattern (`app/domain/factories/user_factory.py`)**: Encapsulating the creation of polymorphic user accounts and their associated profiles.

---

## 2. Assigned Database Models (5 Tables)

Member 1 owns the following models in [`app/models/`](file:///Users/akashg/Desktop/Agriculture/Neolithic/app/models/):

| Model Name | Table Name | Purpose | Key Attributes & Foreign Keys |
| :--- | :--- | :--- | :--- |
| **`User`** | `users` | Base account record | `id` (PK, BigInt), `phone` (Unique, Indexed), `role` (`farmer`, `buyer`, `admin`), `created_at` |
| **`Farmer`** | `farmers` | Farmer-specific profile | `id` (PK), `user_id` (FK $\to$ `users.id`, 1-to-1), `name`, `district`, `fpo_id` (FK $\to$ `fpos.id`), `location` (PostGIS Point) |
| **`Buyer`** | `buyers` | Buyer-specific profile | `id` (PK), `user_id` (FK $\to$ `users.id`, 1-to-1), `name`, `business_type`, `gst_number`, `verified` |
| **`OtpCode`** | `otp_codes` | Short-lived auth codes | `id` (PK), `phone`, `code`, `expires_at`, `used` |
| **`FPO`** | `fpos` | Farmer Producer Org | `id` (PK), `name`, `district`, `reg_number` |

---

## 3. Assigned REST APIs (Endpoints & Contracts)

Member 1 owns the authentication and user router in [`app/routers/auth.py`](file:///Users/akashg/Desktop/Agriculture/Neolithic/app/routers/auth.py) and [`app/routers/fpo.py`](file:///Users/akashg/Desktop/Agriculture/Neolithic/app/routers/fpo.py):

| Method | Endpoint | Request Payload | Response Schema | Description |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/auth/otp/request` | `{"phone": "9822011111"}` | `{"message": "OTP sent", "dev_otp": "123456"}` | Throttled OTP issuance (3 req / 10 min) |
| `POST` | `/api/v1/auth/otp/verify` | `{"phone": "9822011111", "code": "123456"}` | `{"token": "jwt...", "user": {...}}` | Validates OTP and returns Bearer JWT |
| `POST` | `/api/v1/auth/register` | `{"phone": "...", "role": "farmer", "name": "...", "district": "Nashik"}` | `{"token": "jwt...", "user": {...}}` | Creates User + Farmer/Buyer profile via Factory |
| `GET` | `/api/v1/auth/me` | *Headers: Bearer Token* | `UserOut` | Returns authenticated user profile |
| `GET` | `/api/v1/fpo/farmers` | *Headers: Bearer Token (FPO)* | `List[FarmerOut]` | Lists all farmers registered under this FPO |

---

## 4. GoF Design Patterns Implementation

### Pattern 1: Repository Pattern (Structural / Architectural)
- **Problem Solved**: Direct database queries in API routes violate Single Responsibility and create tight coupling to SQLAlchemy.
- **Implementation**:
  - `IRepository[T]` (Abstract Interface with generic typing).
  - `SQLAlchemyBaseRepository[T]` (Concrete base class implementing CRUD).
  - `UserRepository` (Extends base repository with domain-specific queries like `get_by_phone()`).

```python
# app/repositories/base.py
from typing import TypeVar, Generic, Type, Optional, List
from abc import ABC, abstractmethod
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

T = TypeVar("T")

class IRepository(ABC, Generic[T]):
    @abstractmethod
    async def get_by_id(self, id: int) -> Optional[T]: ...
    
    @abstractmethod
    async def list(self, skip: int = 0, limit: int = 100) -> List[T]: ...
    
    @abstractmethod
    async def create(self, entity: T) -> T: ...
    
    @abstractmethod
    async def update(self, entity: T) -> T: ...
    
    @abstractmethod
    async def delete(self, id: int) -> bool: ...

class SQLAlchemyBaseRepository(IRepository[T]):
    def __init__(self, session: AsyncSession, model_cls: Type[T]):
        self.session = session
        self.model_cls = model_cls

    async def get_by_id(self, id: int) -> Optional[T]:
        return await self.session.get(self.model_cls, id)

    async def list(self, skip: int = 0, limit: int = 100) -> List[T]:
        res = await self.session.execute(select(self.model_cls).offset(skip).limit(limit))
        return res.scalars().all()

    async def create(self, entity: T) -> T:
        self.session.add(entity)
        await self.session.commit()
        await self.session.refresh(entity)
        return entity
```

### Pattern 2: Factory Method Pattern (Creational)
- **Problem Solved**: Creating a `User` requires polymorphically creating either a `Farmer` profile or a `Buyer` profile based on dynamic runtime data.
- **Implementation**: `UserFactory.create_user(role, data)`:

```python
# app/domain/factories/user_factory.py
from abc import ABC, abstractmethod
from app.models.user import User, Farmer, Buyer

class UserFactory:
    @staticmethod
    def create_user_profile(user: User, payload: dict):
        role = payload.get("role", "").lower()
        if role == "farmer":
            return Farmer(
                user_id=user.id,
                name=payload.get("name"),
                district=payload.get("district"),
                fpo_id=payload.get("fpo_id")
            )
        elif role == "buyer":
            return Buyer(
                user_id=user.id,
                name=payload.get("name"),
                business_type=payload.get("business_type", "trader"),
                gst_number=payload.get("gst_number")
            )
        else:
            raise ValueError(f"Invalid user role: {role}")
```

---

## 5. SOLID Principles Proof Matrix (Member 1)

1. **Single Responsibility Principle (SRP)**:
   - `OtpService` handles only OTP cryptographic generation, hashing, and 10-minute expiry checks.
   - `UserRepository` handles only database query execution.
   - `AuthRouter` handles only HTTP request serialization and status codes.
2. **Open/Closed Principle (OCP)**:
   - To add a new role (e.g. `LogisticsOperator` or `WarehouseInspector`), we extend `UserFactory` and add a new model without modifying the existing `AuthService` registration flow.
3. **Liskov Substitution Principle (LSP)**:
   - `Farmer` and `Buyer` extend `User` profile relationships. Functions expecting a verified base `User` operate correctly regardless of concrete role.
4. **Interface Segregation Principle (ISP)**:
   - `IRepository` cleanly defines atomic data-access operations without forcing clients to depend on ORM session management internals.
5. **Dependency Inversion Principle (DIP)**:
   - `AuthService` depends on the abstraction `IRepository[User]`, injected via FastAPI's `Depends()`, enabling 100% mocked unit testing.

---

## 6. Pytest Automated Test Suite

Save in `tests/test_member_1_auth_repo.py`:

```python
import pytest
from app.models.user import User, Farmer, Buyer
from app.domain.factories.user_factory import UserFactory

def test_user_factory_creates_farmer():
    user = User(id=1, phone="9822011111", role="farmer")
    farmer = UserFactory.create_user_profile(user, {"role": "farmer", "name": "Ramesh", "district": "Nashik"})
    assert isinstance(farmer, Farmer)
    assert farmer.user_id == 1
    assert farmer.name == "Ramesh"

def test_user_factory_creates_buyer():
    user = User(id=2, phone="9822022222", role="buyer")
    buyer = UserFactory.create_user_profile(user, {"role": "buyer", "name": "Reliance Fresh", "gst_number": "27ABCDE1234F1Z5"})
    assert isinstance(buyer, Buyer)
    assert buyer.user_id == 2
    assert buyer.gst_number == "27ABCDE1234F1Z5"

def test_user_factory_invalid_role_raises():
    user = User(id=3, phone="9822033333", role="invalid")
    with pytest.raises(ValueError):
        UserFactory.create_user_profile(user, {"role": "hacker"})
```

---

## 7. Faculty Viva Defense Guide (Member 1)

* **Faculty Q: "Why did you use the Factory Method pattern instead of just creating the objects directly in the API router?"**
  * *Answer:* *"If we instantiated `Farmer` or `Buyer` directly in `auth.py`, the HTTP controller would be tightly coupled to database entity construction, violating Single Responsibility and Open/Closed principles. Using `UserFactory`, the router simply asks the factory for the appropriate domain entity. If the government adds a third role, like 'Agri-Inspector', we add one line in the factory without touching the authentication pipeline."*

* **Faculty Q: "Explain how Dependency Inversion (DIP) is achieved in your repository pattern."**
  * *Answer:* *"Our service layer never imports or calls SQLAlchemy's `session.execute()` directly. Instead, `AuthService` declares a dependency on the abstract interface `IRepository[User]`. At runtime, FastAPI injects the concrete `SQLAlchemyBaseRepository`. This allows us to swap the database for an in-memory repository during testing without changing one line of business logic."*

