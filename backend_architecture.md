# AgriSense — Detailed Backend Architecture & Implementation Guide

### SIH PS 26132 | Pin-to-Pin Backend Blueprint for Parallel Team Development

> **Purpose:** This document is the single source of truth for the backend. Every teammate reads their section, sets up the shared scaffold once, and builds their module independently. No one blocks anyone else.

---

## Table of Contents

1. [Tech Stack & Tooling](#1-tech-stack--tooling)
2. [Project Setup & Bootstrap](#2-project-setup--bootstrap)
3. [Folder Structure](#3-folder-structure)
4. [Shared Scaffold — What Gets Built First](#4-shared-scaffold--what-gets-built-first)
5. [Database Schema & Migrations](#5-database-schema--migrations)
6. [Authentication & Authorization Middleware](#6-authentication--authorization-middleware)
7. [API Contracts — Endpoint-by-Endpoint](#7-api-contracts--endpoint-by-endpoint)
8. [AI Pipeline Integration](#8-ai-pipeline-integration)
9. [Error Handling & Response Format](#9-error-handling--response-format)
10. [Security Checklist](#10-security-checklist)
11. [Environment Variables](#11-environment-variables)
12. [Docker & Deployment](#12-docker--deployment)
13. [Team Ownership & Parallel Work Map](#13-team-ownership--parallel-work-map)
14. [Testing Strategy](#14-testing-strategy)
15. [Git Workflow](#15-git-workflow)

---

## 1. Tech Stack & Tooling

| Layer | Technology | Why |
|---|---|---|
| **API Framework** | FastAPI (Python 3.11+) | Async, auto-docs (Swagger), Pydantic validation |
| **Database** | PostgreSQL 15 (Docker) | Relational, JSONB for flexible fields |
| **ORM** | SQLAlchemy 2.0 (async) + Alembic | Typed models, migration versioning |
| **Auth** | python-jose (JWT) + passlib (bcrypt) | Industry standard token auth |
| **Payments** | Razorpay Python SDK (test mode) | Indian payment gateway, free test keys |
| **File Storage** | S3-compatible (MinIO locally / AWS S3 prod) | Lot images, call logs |
| **Task Queue** | None for prototype (inline async) | Keep infra simple for 2-day build |
| **AI/ML** | TensorFlow (TFT), LightGBM, scikit-learn | Pre-trained models loaded at startup |
| **Containerisation** | Docker + docker-compose | Single command to run everything |
| **API Docs** | Auto-generated Swagger at `/docs` | Built into FastAPI |

---

## 2. Project Setup & Bootstrap

### 2.1 Prerequisites

```bash
# Every teammate needs:
python 3.11+
docker & docker-compose
git
```

### 2.2 Initial Setup (run once)

```bash
# Clone the repo
git clone <repo-url> && cd agrisense-backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
# Edit .env with your local values (see Section 11)

# Start PostgreSQL + MinIO via Docker
docker-compose up -d postgres minio

# Run database migrations
alembic upgrade head

# Seed initial data (mandi locations, demo logistics providers)
python scripts/seed_data.py

# Start the dev server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2.3 Verify Setup

- Swagger UI: `http://localhost:8000/docs`
- Health check: `GET http://localhost:8000/health` → `{"status": "ok", "db": "connected"}`

---

## 3. Folder Structure

```
agrisense-backend/
├── app/
│   ├── main.py                    # FastAPI app entry, lifespan events, CORS
│   ├── config.py                  # Settings from .env (Pydantic BaseSettings)
│   ├── database.py                # Async engine, sessionmaker, get_db dependency
│   │
│   ├── models/                    # SQLAlchemy ORM models (1 file per table group)
│   │   ├── __init__.py
│   │   ├── user.py                # users, farmers, buyers
│   │   ├── fpo.py                 # fpos
│   │   ├── lot.py                 # lots, batch_lot_members
│   │   ├── mandi.py               # mandi_locations, price_forecasts
│   │   ├── demand.py              # buyer_demand
│   │   ├── offer.py               # offers, offer_lots
│   │   ├── transaction.py         # transactions, transaction_events
│   │   ├── logistics.py           # logistics_providers
│   │   ├── dispute.py             # disputes
│   │   └── voice.py               # call_sessions, voice_interactions (Tier 3)
│   │
│   ├── schemas/                   # Pydantic request/response schemas
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── user.py
│   │   ├── lot.py
│   │   ├── demand.py
│   │   ├── offer.py
│   │   ├── transaction.py
│   │   ├── logistics.py
│   │   ├── dispute.py
│   │   ├── mandi.py
│   │   ├── ai.py
│   │   └── voice.py               # Tier 3
│   │
│   ├── routers/                   # API route handlers (1 file per domain)
│   │   ├── __init__.py
│   │   ├── auth.py                # /auth/*
│   │   ├── users.py               # /users/*
│   │   ├── lots.py                # /lots/*
│   │   ├── demands.py             # /demands/*
│   │   ├── offers.py              # /offers/*
│   │   ├── transactions.py        # /transactions/*
│   │   ├── logistics.py           # /logistics/*
│   │   ├── disputes.py            # /disputes/*
│   │   ├── fpo.py                 # /fpo/*
│   │   ├── mandi.py               # /mandi-locations
│   │   ├── ai.py                  # /ai/*
│   │   └── voice.py               # /voice/*, /calls/* (Tier 3)
│   │
│   ├── services/                  # Business logic (routers call these, never raw SQL)
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── lot_service.py
│   │   ├── demand_service.py
│   │   ├── offer_service.py
│   │   ├── transaction_service.py
│   │   ├── dispute_service.py
│   │   ├── fpo_service.py
│   │   ├── logistics_service.py
│   │   ├── matching_service.py
│   │   └── voice_service.py       # Tier 3
│   │
│   ├── engines/                   # AI/ML pipeline modules
│   │   ├── __init__.py
│   │   ├── price_engine.py        # TFT + LightGBM forecast
│   │   ├── grading_engine.py      # Self-assay rule engine
│   │   ├── matching_engine.py     # Greedy multi-lot matcher
│   │   ├── window_engine.py       # Sale-window + refusal logic
│   │   └── voice_engine.py        # TTS/STT via Bhashini (Tier 3)
│   │
│   ├── middleware/                 # Custom middleware
│   │   ├── __init__.py
│   │   └── error_handler.py       # Global exception handling
│   │
│   ├── dependencies/              # FastAPI dependencies (DI)
│   │   ├── __init__.py
│   │   ├── auth.py                # get_current_user, require_role
│   │   └── database.py            # get_db session
│   │
│   └── utils/                     # Shared utilities
│       ├── __init__.py
│       ├── haversine.py           # Distance calculation
│       ├── money.py               # Paise formatting helpers
│       └── s3.py                  # File upload/download
│
├── ai_models/                     # Pre-trained model artifacts (git-lfs or .gitignore)
│   ├── tft_model/
│   └── lgbm_model.pkl
│
├── alembic/                       # Database migrations
│   ├── versions/
│   └── env.py
│
├── scripts/
│   ├── seed_data.py               # Seed mandi_locations, demo logistics, demo buyers
│   └── generate_forecasts.py      # Batch-generate price_forecasts for demo
│
├── tests/
│   ├── conftest.py                # Shared fixtures (test DB, test client, auth tokens)
│   ├── test_auth.py
│   ├── test_lots.py
│   ├── test_offers.py
│   ├── test_matching.py
│   ├── test_price_engine.py
│   └── test_window_engine.py
│
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── alembic.ini
├── .env.example
└── README.md
```

> **IMPORTANT CONVENTION:** Routers handle HTTP concerns only (parse request, call service, return response). Services contain business logic. Engines contain AI/ML logic. Models are pure data. This separation is what allows 6 people to work without merge conflicts.

---

## 4. Shared Scaffold — What Gets Built First

**Before anyone starts their feature, the following must exist (Akash builds this in the first 1–2 hours):**

### 4.1 `app/main.py`

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine
from app.engines.price_engine import price_engine  # singleton
from app.routers import (
    auth, users, lots, demands, offers,
    transactions, logistics, disputes, fpo, mandi, ai
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: load AI models into memory
    price_engine.load_models()
    yield
    # Shutdown: cleanup

app = FastAPI(
    title="AgriSense API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Lock down in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(lots.router, prefix="/lots", tags=["Lots"])
app.include_router(demands.router, prefix="/demands", tags=["Demands"])
app.include_router(offers.router, prefix="/offers", tags=["Offers"])
app.include_router(transactions.router, prefix="/transactions", tags=["Transactions"])
app.include_router(logistics.router, prefix="/logistics", tags=["Logistics"])
app.include_router(disputes.router, prefix="/disputes", tags=["Disputes"])
app.include_router(fpo.router, prefix="/fpo", tags=["FPO"])
app.include_router(mandi.router, prefix="/mandi-locations", tags=["Mandi"])
app.include_router(ai.router, prefix="/ai", tags=["AI"])

@app.get("/health")
async def health():
    return {"status": "ok"}
```

### 4.2 `app/config.py`

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://agrisense:agrisense@localhost:5432/agrisense"
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440  # 24 hours
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    S3_ENDPOINT: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET: str = "agrisense"
    BHASHINI_API_KEY: str = ""       # Tier 3
    AGORA_APP_ID: str = ""           # Tier 3
    AGORA_APP_CERTIFICATE: str = ""  # Tier 3

    class Config:
        env_file = ".env"

settings = Settings()
```

### 4.3 `app/database.py`

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

### 4.4 `app/dependencies/auth.py`

```python
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.user import User

security = HTTPBearer()

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: AsyncSession = Depends(get_db),
) -> User:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        user_id: int = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user

def require_role(*roles: str):
    """Dependency factory: require the current user to have one of the given roles."""
    async def _check(user: User = Depends(get_current_user)):
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)  # 404 not 403
        return user
    return _check
```

---

## 5. Database Schema & Migrations

### 5.1 ORM Models

#### `app/models/user.py`

```python
from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(15), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False)  # 'farmer', 'buyer', 'fpo_admin'
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    preferred_language = Column(String(10), default="en")
    verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    farmer_profile = relationship("Farmer", back_populates="user", uselist=False)
    buyer_profile = relationship("Buyer", back_populates="user", uselist=False)

class Farmer(Base):
    __tablename__ = "farmers"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    fpo_id = Column(Integer, ForeignKey("fpos.id"), nullable=True)

    user = relationship("User", back_populates="farmer_profile")
    fpo = relationship("FPO", back_populates="farmers")

class Buyer(Base):
    __tablename__ = "buyers"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    company_name = Column(String(200), nullable=True)
    verified_status = Column(Boolean, default=False)

    user = relationship("User", back_populates="buyer_profile")
```

#### `app/models/fpo.py`

```python
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.database import Base

class FPO(Base):
    __tablename__ = "fpos"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    region = Column(String(200), nullable=True)

    farmers = relationship("Farmer", back_populates="fpo")
```

#### `app/models/lot.py`

```python
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import relationship
from app.database import Base

class Lot(Base):
    __tablename__ = "lots"

    id = Column(Integer, primary_key=True, index=True)
    farmer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    fpo_id = Column(Integer, ForeignKey("fpos.id"), nullable=True)
    crop = Column(String(100), nullable=False, index=True)
    quantity_kg = Column(Integer, nullable=False)
    grade = Column(String(5), nullable=True)  # A, B, C — set by grading engine
    image_url = Column(String(500), nullable=True)
    self_assay_answers = Column(JSON, nullable=True)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    price_min_paise_per_qtl = Column(Integer, nullable=True)
    price_mid_paise_per_qtl = Column(Integer, nullable=True)
    price_max_paise_per_qtl = Column(Integer, nullable=True)
    status = Column(String(30), default="active", index=True)
    # Statuses: active, matched, sold, cancelled, aggregated
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    farmer = relationship("User")
    offer_allocations = relationship("OfferLot", back_populates="lot")

class BatchLotMember(Base):
    __tablename__ = "batch_lot_members"

    id = Column(Integer, primary_key=True)
    batch_lot_id = Column(Integer, ForeignKey("lots.id"), nullable=False)
    source_lot_id = Column(Integer, ForeignKey("lots.id"), nullable=False)
    quantity_contributed_kg = Column(Integer, nullable=False)
```

#### `app/models/mandi.py`

```python
from sqlalchemy import Column, Integer, String, Float, DateTime, func
from app.database import Base

class MandiLocation(Base):
    __tablename__ = "mandi_locations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    district = Column(String(200), nullable=False)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)

class PriceForecast(Base):
    __tablename__ = "price_forecasts"

    id = Column(Integer, primary_key=True, index=True)
    mandi = Column(String(200), nullable=False, index=True)
    commodity = Column(String(100), nullable=False, index=True)
    date = Column(DateTime, nullable=False)
    p10_paise = Column(Integer, nullable=False)
    p50_paise = Column(Integer, nullable=False)
    p90_paise = Column(Integer, nullable=False)
    forecast_confidence = Column(Float, nullable=False)  # 0.0 to 1.0
    generated_at = Column(DateTime(timezone=True), server_default=func.now())
```

#### `app/models/demand.py`

```python
from sqlalchemy import Column, Integer, String, Float, ForeignKey
from app.database import Base

class BuyerDemand(Base):
    __tablename__ = "buyer_demand"

    id = Column(Integer, primary_key=True, index=True)
    buyer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    crop = Column(String(100), nullable=False)
    desired_qty_kg = Column(Integer, nullable=False)
    desired_grade = Column(String(5), nullable=True)
    max_price_paise_per_qtl = Column(Integer, nullable=True)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    source = Column(String(10), default="real")  # 'real' or 'demo'
```

#### `app/models/offer.py`

```python
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base

class Offer(Base):
    __tablename__ = "offers"

    id = Column(Integer, primary_key=True, index=True)
    buyer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    offered_price_paise_per_qtl = Column(Integer, nullable=False)
    total_quantity_kg = Column(Integer, nullable=False)
    status = Column(String(30), default="pending")
    # Statuses: pending, accepted, rejected, cancelled, paid
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    lots = relationship("OfferLot", back_populates="offer")

class OfferLot(Base):
    __tablename__ = "offer_lots"

    offer_id = Column(Integer, ForeignKey("offers.id"), primary_key=True)
    lot_id = Column(Integer, ForeignKey("lots.id"), primary_key=True)
    quantity_allocated_kg = Column(Integer, nullable=False)

    offer = relationship("Offer", back_populates="lots")
    lot = relationship("Lot", back_populates="offer_allocations")
```

#### `app/models/transaction.py`

```python
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, func
from app.database import Base

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    offer_id = Column(Integer, ForeignKey("offers.id"), nullable=False, unique=True)
    amount_paise = Column(Integer, nullable=False)
    razorpay_order_id = Column(String(100), nullable=True)
    payment_status = Column(String(30), default="pending")
    # Statuses: pending, created, paid, failed, refunded
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class TransactionEvent(Base):
    __tablename__ = "transaction_events"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False, index=True)
    event_type = Column(String(50), nullable=False)
    # Types: order_created, payment_authorized, payment_captured, payment_failed, refund_initiated
    payload = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

#### `app/models/logistics.py`

```python
from sqlalchemy import Column, Integer, String, Float
from app.database import Base

class LogisticsProvider(Base):
    __tablename__ = "logistics_providers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    type = Column(String(20), nullable=False)  # 'storage' or 'transport'
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    capacity_kg = Column(Integer, nullable=True)
    contact = Column(String(50), nullable=True)
    source = Column(String(10), default="demo")  # 'real' or 'demo'
```

#### `app/models/dispute.py`

```python
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from app.database import Base

class Dispute(Base):
    __tablename__ = "disputes"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False)
    raised_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    reason = Column(String(500), nullable=False)
    status = Column(String(30), default="open")
    # Statuses: open, under_review, resolved, dismissed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

#### `app/models/voice.py` (Tier 3)

```python
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from app.database import Base

class CallSession(Base):
    __tablename__ = "call_sessions"

    id = Column(Integer, primary_key=True, index=True)
    offer_id = Column(Integer, ForeignKey("offers.id"), nullable=False)
    farmer_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    buyer_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    provider_session_id = Column(String(200), nullable=True)
    status = Column(String(30), default="initiated")
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    ended_at = Column(DateTime(timezone=True), nullable=True)

class VoiceInteraction(Base):
    __tablename__ = "voice_interactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    audio_ref = Column(String(500), nullable=True)
    transcript = Column(String, nullable=True)
    language = Column(String(10), nullable=True)
    intent_detected = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

### 5.2 Migration Workflow

```bash
# After creating/modifying any model:
alembic revision --autogenerate -m "description of change"
alembic upgrade head

# To rollback:
alembic downgrade -1
```

> **WARNING:** Only Akash runs the initial migration that creates all tables. After that, each person creates their own migration file for any schema changes they need. Always pull latest before generating a migration.

---

## 6. Authentication & Authorization Middleware

### 6.1 Auth Flow

```
┌──────────┐     POST /auth/register      ┌──────────┐
│  Client   │ ───────────────────────────→ │  Backend  │
│  (App)    │     { phone, password, ... } │           │
│           │ ←─────────────────────────── │           │
│           │     { user, token }          │           │
│           │                              │           │
│           │     POST /auth/login         │           │
│           │ ───────────────────────────→ │           │
│           │     { phone, password }      │           │
│           │ ←─────────────────────────── │           │
│           │     { user, token }          │           │
│           │                              │           │
│           │     GET /lots (+ Bearer)     │           │
│           │ ───────────────────────────→ │           │
│           │     Authorization: Bearer <JWT>         │
│           │ ←─────────────────────────── │           │
│           │     { lots: [...] }          │           │
└──────────┘                              └──────────┘
```

### 6.2 JWT Payload Structure

```json
{
  "user_id": 42,
  "role": "farmer",
  "exp": 1696012800
}
```

### 6.3 Using Auth in Routers

```python
from fastapi import APIRouter, Depends
from app.dependencies.auth import get_current_user, require_role
from app.models.user import User

router = APIRouter()

# Any authenticated user
@router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    return {"id": user.id, "name": user.name, "role": user.role}

# Only farmers
@router.post("/lots")
async def create_lot(
    payload: LotCreate,
    user: User = Depends(require_role("farmer")),
):
    ...

# Only buyers
@router.post("/demands")
async def create_demand(
    payload: DemandCreate,
    user: User = Depends(require_role("buyer")),
):
    ...

# Only FPO admins
@router.post("/fpo/aggregate")
async def aggregate_lots(
    payload: AggregateRequest,
    user: User = Depends(require_role("fpo_admin")),
):
    ...
```

> **SECURITY RULE:** NEVER accept `user_id` or `farmer_id` from query params for ownership. ALWAYS derive from `get_current_user`. Return 404 (not 403) for unauthorized access attempts.

---

## 7. API Contracts — Endpoint-by-Endpoint

### 7.1 Auth — `app/routers/auth.py` (Owner: Akash)

#### `POST /auth/register`

```
Request:
{
  "name": "Rajesh Kumar",
  "phone": "9876543210",
  "password": "securepass123",
  "role": "farmer",               // "farmer" | "buyer" | "fpo_admin"
  "lat": 28.6139,                 // optional
  "lng": 77.2090,                 // optional
  "preferred_language": "hi",     // optional, default "en"
  "company_name": null,           // required only for role=buyer
  "fpo_id": null                  // optional, for farmer
}

Response (201):
{
  "user": {
    "id": 42,
    "name": "Rajesh Kumar",
    "phone": "9876543210",
    "role": "farmer",
    "verified": false,
    "preferred_language": "hi"
  },
  "token": "eyJhbGciOiJIUzI1NiIs..."
}

Errors:
  409: { "detail": "Phone number already registered" }
  422: Pydantic validation error
```

#### `POST /auth/login`

```
Request:
{
  "phone": "9876543210",
  "password": "securepass123"
}

Response (200):
{
  "user": { ... },  // same shape as register response
  "token": "eyJhbGciOiJIUzI1NiIs..."
}

Errors:
  401: { "detail": "Invalid credentials" }
```

---

### 7.2 Users — `app/routers/users.py` (Owner: Akash)

#### `GET /users/me`

```
Headers: Authorization: Bearer <JWT>

Response (200):
{
  "id": 42,
  "name": "Rajesh Kumar",
  "phone": "9876543210",
  "role": "farmer",
  "lat": 28.6139,
  "lng": 77.2090,
  "preferred_language": "hi",
  "verified": false,
  "created_at": "2026-09-05T10:00:00Z",
  "farmer_profile": {
    "fpo_id": 3
  }
}
```

---

### 7.3 Mandi Locations — `app/routers/mandi.py` (Owner: Kartik)

#### `GET /mandi-locations`

```
Query params: ?district= (optional filter)

Response (200):
{
  "locations": [
    {
      "id": 1,
      "name": "Azadpur Mandi",
      "district": "Delhi",
      "lat": 28.7041,
      "lng": 77.1025
    },
    ...
  ]
}
```

---

### 7.4 Lots — `app/routers/lots.py` (Owner: Akash)

#### `POST /lots`

```
Headers: Authorization: Bearer <JWT> (role: farmer)

Request:
{
  "crop": "wheat",
  "quantity_kg": 500,
  "lat": 28.6139,
  "lng": 77.2090,
  "image_url": null               // optional, filled after S3 upload
}

Internal flow:
  1. Create lot row with status="active"
  2. Call price_engine.predict(nearest_mandi, crop, today) → set price_min/mid/max
  3. Return lot with price band

Response (201):
{
  "id": 15,
  "farmer_id": 42,
  "crop": "wheat",
  "quantity_kg": 500,
  "grade": null,                  // null until self-assay is completed
  "price_min_paise_per_qtl": 190000,
  "price_mid_paise_per_qtl": 210000,
  "price_max_paise_per_qtl": 230000,
  "status": "active",
  "created_at": "2026-09-05T10:30:00Z"
}
```

#### `GET /lots/{id}`

```
Headers: Authorization: Bearer <JWT>

Access control:
  - Farmer who owns the lot: ✅
  - Buyer who has an active offer on this lot: ✅
  - Anyone else: 404

Response (200):
{
  "id": 15,
  "farmer_id": 42,
  "crop": "wheat",
  "quantity_kg": 500,
  "grade": "B",
  "self_assay_answers": { ... },
  "image_url": "https://s3.../lot-15.jpg",
  "lat": 28.6139,
  "lng": 77.2090,
  "price_min_paise_per_qtl": 190000,
  "price_mid_paise_per_qtl": 210000,
  "price_max_paise_per_qtl": 230000,
  "status": "active",
  "created_at": "2026-09-05T10:30:00Z"
}
```

#### `GET /lots?status=active`

```
Headers: Authorization: Bearer <JWT> (role: farmer)

Returns only lots owned by the JWT user.
Query params: ?status= (optional filter)

Response (200):
{
  "lots": [ ... ]
}
```

#### `POST /lots/{id}/self-assay`

```
Headers: Authorization: Bearer <JWT> (role: farmer, must own the lot)

Request:
{
  "size_uniformity": "high",       // "high" | "medium" | "low"
  "color_uniformity": "high",      // "high" | "medium" | "low"
  "damage_percent": 5,             // 0-100
  "sprouting_percent": 2,          // 0-100
  "moisture_level": "normal",      // "dry" | "normal" | "moist"
  "foreign_matter": "low"          // "none" | "low" | "moderate" | "high"
}

Internal flow:
  1. Save answers in lot.self_assay_answers
  2. Call grading_engine.grade(answers) → grade + tip
  3. Update lot.grade

Response (200):
{
  "lot_id": 15,
  "grade": "B",
  "improvement_tip": "Reduce moisture content by sun-drying for 2-3 days to achieve Grade A.",
  "self_assay_answers": { ... }
}
```

#### `GET /lots/{id}/price-suggestion`

```
Headers: Authorization: Bearer <JWT> (must own or have offer on lot)

Response (200):
{
  "lot_id": 15,
  "price_band": {
    "min_paise_per_qtl": 190000,
    "mid_paise_per_qtl": 210000,
    "max_paise_per_qtl": 230000
  },
  "sale_window": {
    "recommendation": "HOLD",       // "SELL" | "HOLD" | "NO_ADVICE"
    "expected_gain_paise": 12000,
    "worst_case_paise": -3000,
    "itemised_costs": {
      "transport_paise": 2000,
      "commission_paise": 1500,
      "storage_paise": 1000,
      "spoilage_estimate_paise": 500
    },
    "hold_until_date": "2026-09-12",
    "reason": null                  // populated only when recommendation="NO_ADVICE"
  }
}
```

#### `GET /lots/{id}/matches`

```
Headers: Authorization: Bearer <JWT> (must own the lot)

Response (200):
{
  "lot_id": 15,
  "matches": [
    {
      "buyer_demand_id": 7,
      "buyer_name": "AgriCorp Foods",
      "crop": "wheat",
      "desired_qty_kg": 500,
      "max_price_paise_per_qtl": 220000,
      "distance_km": 45.3,
      "match_score": 0.87
    },
    ...
  ]
}
```

---

### 7.5 Demands — `app/routers/demands.py` (Owner: Nilesh)

#### `POST /demands`

```
Headers: Authorization: Bearer <JWT> (role: buyer)

Request:
{
  "crop": "wheat",
  "desired_qty_kg": 2000,
  "desired_grade": "A",           // optional
  "max_price_paise_per_qtl": 220000,  // optional
  "lat": 28.6139,
  "lng": 77.2090
}

Response (201):
{
  "id": 7,
  "buyer_id": 55,
  "crop": "wheat",
  "desired_qty_kg": 2000,
  "desired_grade": "A",
  "max_price_paise_per_qtl": 220000,
  "lat": 28.6139,
  "lng": 77.2090
}
```

#### `GET /demands`

```
Headers: Authorization: Bearer <JWT> (role: buyer)

Returns only demands owned by the JWT user.

Response (200):
{
  "demands": [ ... ]
}
```

#### `GET /demands/{id}/matches`

```
Headers: Authorization: Bearer <JWT> (must own the demand)

Internal flow:
  Matching engine finds the optimal multi-lot combination:
  - Filters lots by crop, grade, price fit
  - Ranks by proximity + grade + price
  - Greedily combines lots until desired_qty_kg is covered

Response (200):
{
  "demand_id": 7,
  "total_available_kg": 2100,
  "combination": [
    {
      "lot_id": 15,
      "farmer_name": "Rajesh Kumar",
      "crop": "wheat",
      "grade": "A",
      "available_kg": 500,
      "allocated_kg": 500,
      "price_mid_paise_per_qtl": 210000,
      "distance_km": 45.3,
      "match_score": 0.92
    },
    {
      "lot_id": 22,
      "farmer_name": "Suresh Patel",
      "crop": "wheat",
      "grade": "A",
      "available_kg": 1800,
      "allocated_kg": 1500,
      "price_mid_paise_per_qtl": 205000,
      "distance_km": 67.1,
      "match_score": 0.85
    }
  ],
  "estimated_total_cost_paise": 41750000
}
```

---

### 7.6 Offers — `app/routers/offers.py` (Owner: Nilesh)

#### `POST /offers`

```
Headers: Authorization: Bearer <JWT> (role: buyer)

Request:
{
  "lots": [
    { "lot_id": 15, "quantity_allocated_kg": 500 },
    { "lot_id": 22, "quantity_allocated_kg": 1500 }
  ],
  "offered_price_paise_per_qtl": 215000
}

Internal flow:
  1. Validate each lot exists and is "active"
  2. Validate total quantity doesn't exceed lot availability
  3. Create offer + offer_lots rows
  4. Set offer.total_quantity_kg = sum of allocations

Response (201):
{
  "id": 31,
  "buyer_id": 55,
  "offered_price_paise_per_qtl": 215000,
  "total_quantity_kg": 2000,
  "status": "pending",
  "lots": [
    { "lot_id": 15, "quantity_allocated_kg": 500 },
    { "lot_id": 22, "quantity_allocated_kg": 1500 }
  ],
  "created_at": "2026-09-05T11:00:00Z"
}
```

#### `PATCH /offers/{id}`

```
Headers: Authorization: Bearer <JWT> (farmer who owns at least one lot in the offer)

Request:
{
  "action": "accept"   // "accept" | "reject"
}

Internal flow:
  On accept:
    1. Update offer.status = "accepted"
    2. Update each lot's status to "matched"
    3. Block lot from receiving other offers
  On reject:
    1. Update offer.status = "rejected"
    2. Lots remain "active"

Response (200):
{
  "id": 31,
  "status": "accepted",
  ...
}

Errors:
  404: Offer not found or user doesn't own any lot in the offer
  400: { "detail": "Offer is not in pending status" }
```

---

### 7.7 Transactions — `app/routers/transactions.py` (Owner: Nilesh)

#### `POST /transactions/{offer_id}/create-order`

```
Headers: Authorization: Bearer <JWT> (buyer who owns the offer)

Internal flow:
  1. Verify offer.status == "accepted"
  2. Calculate amount_paise = offered_price × total_quantity / 100
  3. Call Razorpay API: razorpay.order.create(amount, currency="INR")
  4. Create transaction row + TransactionEvent("order_created")
  5. Return razorpay_order_id to client for checkout widget

Response (201):
{
  "transaction_id": 18,
  "offer_id": 31,
  "amount_paise": 43000000,
  "razorpay_order_id": "order_LmZ7xYz12AB",
  "payment_status": "created"
}
```

#### `POST /transactions/webhook`

```
No auth header — verified by Razorpay signature

Request: (Razorpay webhook payload)
{
  "event": "payment.captured",
  "payload": {
    "payment": {
      "entity": {
        "order_id": "order_LmZ7xYz12AB",
        "amount": 43000000,
        "status": "captured"
      }
    }
  }
}

Internal flow:
  1. Verify Razorpay signature (razorpay_webhook_secret)
  2. Find transaction by razorpay_order_id
  3. Update payment_status = "paid"
  4. Append TransactionEvent("payment_captured", payload)
  5. Update offer.status = "paid"
  6. Update lot statuses to "sold"

Response (200): { "status": "ok" }
```

#### `GET /transactions/{id}`

```
Headers: Authorization: Bearer <JWT> (buyer or farmer involved in the offer)

Response (200):
{
  "id": 18,
  "offer_id": 31,
  "amount_paise": 43000000,
  "razorpay_order_id": "order_LmZ7xYz12AB",
  "payment_status": "paid",
  "created_at": "2026-09-05T11:30:00Z",
  "events": [
    {
      "event_type": "order_created",
      "created_at": "2026-09-05T11:30:00Z"
    },
    {
      "event_type": "payment_captured",
      "created_at": "2026-09-05T11:32:15Z"
    }
  ]
}
```

---

### 7.8 Logistics — `app/routers/logistics.py` (Owner: Kartik)

#### `GET /logistics?lat=28.6&lng=77.2`

```
Headers: Authorization: Bearer <JWT>

Query params:
  lat, lng (required) — user's location
  type (optional) — "storage" | "transport"
  radius_km (optional, default 50)

Internal flow:
  Filter by haversine distance, sort by nearest.

Response (200):
{
  "providers": [
    {
      "id": 3,
      "name": "ColdStore Pvt Ltd",
      "type": "storage",
      "lat": 28.62,
      "lng": 77.21,
      "distance_km": 2.3,
      "capacity_kg": 50000,
      "contact": "9876543210",
      "source": "demo"            // honesty badge
    },
    ...
  ]
}
```

---

### 7.9 Disputes — `app/routers/disputes.py` (Owner: Nilesh)

#### `POST /disputes`

```
Headers: Authorization: Bearer <JWT>

Request:
{
  "transaction_id": 18,
  "reason": "Quality mismatch - received Grade C instead of Grade A"
}

Internal flow:
  1. Verify user is buyer or farmer involved in the transaction
  2. Create dispute row

Response (201):
{
  "id": 5,
  "transaction_id": 18,
  "raised_by": 42,
  "reason": "Quality mismatch...",
  "status": "open",
  "created_at": "2026-09-06T09:00:00Z"
}
```

#### `GET /disputes`

```
Returns disputes relevant to the JWT user.
```

#### `PATCH /disputes/{id}`

```
Request: { "status": "resolved" }
Only accessible by fpo_admin or the opposing party.
```

---

### 7.10 FPO — `app/routers/fpo.py` (Owner: Akash)

#### `POST /fpo/aggregate`

```
Headers: Authorization: Bearer <JWT> (role: fpo_admin)

Request:
{
  "lot_ids": [15, 16, 17]
}

Internal flow:
  1. Verify all lots belong to farmers in the FPO admin's FPO
  2. Create a new "batch" lot:
     - crop: must be same across all lots (else 400)
     - quantity_kg: sum
     - grade: weighted or lowest-common grade
     - price bands: recalculated from price engine
  3. Create batch_lot_members entries
  4. Original lots status → "aggregated"

Response (201):
{
  "batch_lot": {
    "id": 50,
    "crop": "wheat",
    "quantity_kg": 1500,
    "grade": "B",
    "price_min_paise_per_qtl": 192000,
    "price_mid_paise_per_qtl": 212000,
    "price_max_paise_per_qtl": 232000,
    "status": "active",
    "member_lots": [
      { "source_lot_id": 15, "quantity_contributed_kg": 500 },
      { "source_lot_id": 16, "quantity_contributed_kg": 400 },
      { "source_lot_id": 17, "quantity_contributed_kg": 600 }
    ]
  }
}
```

---

### 7.11 AI Endpoints — `app/routers/ai.py` (Owner: Nikhil)

#### `GET /ai/price-forecast?mandi=Azadpur&commodity=wheat`

```
Headers: Authorization: Bearer <JWT>

Response (200):
{
  "mandi": "Azadpur",
  "commodity": "wheat",
  "forecasts": [
    {
      "date": "2026-09-06",
      "p10_paise": 188000,
      "p50_paise": 210000,
      "p90_paise": 232000,
      "confidence": 0.82
    },
    {
      "date": "2026-09-07",
      "p10_paise": 190000,
      "p50_paise": 213000,
      "p90_paise": 236000,
      "confidence": 0.78
    },
    ... // 14 days
  ]
}
```

#### `GET /ai/sale-window?lot_id=15`

```
Headers: Authorization: Bearer <JWT> (must own the lot)

Internal flow:
  1. Get lot's crop, nearest mandi
  2. Pull 14-day forecast from price_forecasts table
  3. Run window_engine logic (see Section 8.2)

Response (200) — confident recommendation:
{
  "lot_id": 15,
  "recommendation": "HOLD",
  "expected_gain_paise": 12000,
  "worst_case_paise": -3000,
  "hold_until_date": "2026-09-12",
  "itemised_costs": {
    "transport_paise": 2000,
    "commission_paise": 1500,
    "storage_paise": 1000,
    "spoilage_estimate_paise": 500
  }
}

Response (200) — uncertain / refusal:
{
  "lot_id": 15,
  "recommendation": "NO_ADVICE",
  "reason": "Forecast too uncertain for wheat at Azadpur mandi right now (band width 31%, threshold 25%)"
}
```

---

### 7.12 Voice & Calls (Tier 3) — `app/routers/voice.py` (Owner: Nikhil/Nilesh)

#### `POST /voice/narrate`

```
Request:
{
  "text": "You should hold for 5 more days. Expected gain is ₹120.",
  "language": "hi"
}

Response (200):
{
  "audio_url": "https://s3.../narration-xyz.mp3",
  "language": "hi"
}
```

#### `POST /calls/initiate`

```
Request:
{
  "offer_id": 31
}

Response (200):
{
  "call_session_id": 8,
  "agora_token": "006abc...",
  "channel_name": "offer-31"
}
```

---

## 8. AI Pipeline Integration

### 8.1 Price Engine — `app/engines/price_engine.py` (Owner: Nikhil)

```python
import pickle
import numpy as np

class PriceEngine:
    """Singleton — loaded once at app startup via lifespan."""

    def __init__(self):
        self.tft_model = None
        self.lgbm_model = None

    def load_models(self):
        """Called in FastAPI lifespan startup."""
        # Load TFT (TensorFlow SavedModel or custom)
        # self.tft_model = tf.saved_model.load("ai_models/tft_model")
        with open("ai_models/lgbm_model.pkl", "rb") as f:
            self.lgbm_model = pickle.load(f)

    def predict(self, mandi: str, commodity: str, date: str) -> dict:
        """
        Returns:
          {
            "p10_paise": int,
            "p50_paise": int,
            "p90_paise": int,
            "confidence": float  # 0.0 to 1.0
          }
        """
        # Feature engineering: encode mandi, commodity, date features
        # Run inference on TFT for quantiles
        # Run LightGBM as ensemble/fallback
        # Return merged quantile prediction
        pass

    def predict_range(self, mandi: str, commodity: str, days: int = 14) -> list[dict]:
        """Predict for the next N days. Returns list of daily predictions."""
        pass

# Module-level singleton
price_engine = PriceEngine()
```

### 8.2 Window + Refusal Engine — `app/engines/window_engine.py` (Owner: Nikhil)

```python
from app.engines.price_engine import price_engine

# Configurable thresholds
BAND_WIDTH_THRESHOLD = 0.25  # 25%
TRANSPORT_COST_PAISE_PER_KM = 50
COMMISSION_RATE = 0.025  # 2.5%
STORAGE_COST_PAISE_PER_KG_PER_DAY = 5
SPOILAGE_RATE_PER_DAY = 0.002  # 0.2%

def compute_sale_window(
    crop: str,
    mandi: str,
    quantity_kg: int,
    current_price_mid_paise: int,
    distance_km: float,
) -> dict:
    """
    Algorithm:
    1. Pull p10/p50/p90 for next 14 days
    2. Compute band_width = (p90 - p10) / p50
    3. If band_width > BAND_WIDTH_THRESHOLD:
         return NO_ADVICE + reason
    4. Else:
         For each future day:
           expected_gain = (p50_future - current_mid) × quantity
                         - transport_cost - commission - storage_cost - spoilage
           worst_case = (p10_future - current_mid) × quantity - same costs
         Find the day with max expected_gain where worst_case > 0
         Return HOLD (with that date) or SELL (if today is best)
    """
    forecasts = price_engine.predict_range(mandi, crop, days=14)

    # Check band width on the nearest forecast
    latest = forecasts[0]
    band_width = (latest["p90_paise"] - latest["p10_paise"]) / latest["p50_paise"]

    if band_width > BAND_WIDTH_THRESHOLD:
        return {
            "recommendation": "NO_ADVICE",
            "reason": f"Forecast too uncertain for {crop} at {mandi} "
                      f"(band width {band_width:.0%}, threshold {BAND_WIDTH_THRESHOLD:.0%})"
        }

    best_day = None
    best_gain = 0
    best_worst = 0
    best_costs = {}

    for i, fc in enumerate(forecasts):
        days_from_now = i + 1
        transport = int(distance_km * TRANSPORT_COST_PAISE_PER_KM)
        commission = int(fc["p50_paise"] * quantity_kg / 100 * COMMISSION_RATE)
        storage = int(STORAGE_COST_PAISE_PER_KG_PER_DAY * quantity_kg * days_from_now)
        spoilage = int(current_price_mid_paise * quantity_kg / 100
                       * SPOILAGE_RATE_PER_DAY * days_from_now)
        total_costs = transport + commission + storage + spoilage

        gain = (fc["p50_paise"] - current_price_mid_paise) * quantity_kg // 100 - total_costs
        worst = (fc["p10_paise"] - current_price_mid_paise) * quantity_kg // 100 - total_costs

        if gain > best_gain and worst > -total_costs:
            best_day = i
            best_gain = gain
            best_worst = worst
            best_costs = {
                "transport_paise": transport,
                "commission_paise": commission,
                "storage_paise": storage,
                "spoilage_estimate_paise": spoilage,
            }

    if best_day is None or best_day == 0:
        return {
            "recommendation": "SELL",
            "expected_gain_paise": 0,
            "worst_case_paise": 0,
            "itemised_costs": {},
        }

    return {
        "recommendation": "HOLD",
        "expected_gain_paise": best_gain,
        "worst_case_paise": best_worst,
        "hold_days": best_day + 1,
        "itemised_costs": best_costs,
    }
```

### 8.3 Grading Engine — `app/engines/grading_engine.py` (Owner: Akash)

```python
GRADE_RULES = {
    # Each answer maps to a numeric score (higher = better)
    "size_uniformity":  {"high": 3, "medium": 2, "low": 1},
    "color_uniformity": {"high": 3, "medium": 2, "low": 1},
    "damage_percent":   lambda v: 3 if v < 5 else (2 if v < 15 else 1),
    "sprouting_percent": lambda v: 3 if v < 3 else (2 if v < 10 else 1),
    "moisture_level":   {"dry": 3, "normal": 2, "moist": 1},
    "foreign_matter":   {"none": 3, "low": 2, "moderate": 1, "high": 0},
}

IMPROVEMENT_TIPS = {
    "damage_percent": "Careful handling during harvest reduces damage. Consider sorting out damaged produce before listing.",
    "sprouting_percent": "Store in cool, dark, dry conditions to prevent sprouting.",
    "moisture_level": "Sun-dry produce for 2-3 days to reduce moisture and achieve a higher grade.",
    "foreign_matter": "Clean and sieve the produce to remove foreign matter before listing.",
    "size_uniformity": "Sort produce by size before listing for a more uniform lot.",
    "color_uniformity": "Remove discoloured items before listing for a more uniform lot.",
}

def grade(answers: dict) -> dict:
    """
    Input: dict with keys matching GRADE_RULES
    Output: { "grade": "A" | "B" | "C", "improvement_tip": str }
    """
    total_score = 0
    worst_param = None
    worst_score = 99

    for param, rule in GRADE_RULES.items():
        value = answers.get(param)
        if value is None:
            continue
        if callable(rule):
            score = rule(value)
        else:
            score = rule.get(value, 1)
        total_score += score
        if score < worst_score:
            worst_score = score
            worst_param = param

    max_possible = len(GRADE_RULES) * 3  # 18

    if total_score >= max_possible * 0.8:       # >= 14.4 → 15+
        grade_label = "A"
    elif total_score >= max_possible * 0.55:    # >= 9.9 → 10+
        grade_label = "B"
    else:
        grade_label = "C"

    tip = IMPROVEMENT_TIPS.get(worst_param, "Maintain current quality practices.")

    return {"grade": grade_label, "improvement_tip": tip}
```

### 8.4 Matching Engine — `app/engines/matching_engine.py` (Owner: Nilesh)

```python
from app.utils.haversine import haversine_km

# Weights for scoring
W_GRADE = 0.30
W_PROXIMITY = 0.35
W_PRICE = 0.35

def score_lot(lot, demand) -> float:
    """Score a single lot against a buyer demand. Returns 0.0-1.0."""

    # Grade match
    grade_order = {"A": 3, "B": 2, "C": 1, None: 0}
    if lot.grade == demand.desired_grade:
        grade_score = 1.0
    elif grade_order.get(lot.grade, 0) > grade_order.get(demand.desired_grade, 0):
        grade_score = 0.8  # better than required
    else:
        grade_score = 0.3  # worse than required

    # Proximity (closer = better, max 500km considered)
    dist = haversine_km(lot.lat, lot.lng, demand.lat, demand.lng)
    proximity_score = max(0, 1.0 - dist / 500)

    # Price fit (lot's mid price vs buyer's max price)
    if demand.max_price_paise_per_qtl and lot.price_mid_paise_per_qtl:
        if lot.price_mid_paise_per_qtl <= demand.max_price_paise_per_qtl:
            price_score = 1.0
        else:
            overshoot = (lot.price_mid_paise_per_qtl - demand.max_price_paise_per_qtl) \
                        / demand.max_price_paise_per_qtl
            price_score = max(0, 1.0 - overshoot)
    else:
        price_score = 0.5  # no price preference

    return W_GRADE * grade_score + W_PROXIMITY * proximity_score + W_PRICE * price_score


def match_lots_for_demand(lots: list, demand) -> list[dict]:
    """
    Greedy multi-lot matching.
    Returns list of { lot, allocated_kg, match_score } covering the demand quantity.
    """
    scored = [(lot, score_lot(lot, demand)) for lot in lots if lot.crop == demand.crop]
    scored.sort(key=lambda x: -x[1])  # highest score first

    result = []
    remaining_kg = demand.desired_qty_kg

    for lot, score in scored:
        if remaining_kg <= 0:
            break
        if lot.status != "active":
            continue
        allocated = min(lot.quantity_kg, remaining_kg)
        result.append({
            "lot": lot,
            "allocated_kg": allocated,
            "match_score": round(score, 3),
        })
        remaining_kg -= allocated

    return result


def match_demands_for_lot(demands: list, lot) -> list[dict]:
    """
    Find buyer demands matching a single lot. Returns ranked list.
    """
    scored = [(d, score_lot(lot, d)) for d in demands if d.crop == lot.crop]
    scored.sort(key=lambda x: -x[1])
    return [{"demand": d, "match_score": round(s, 3)} for d, s in scored[:10]]
```

### 8.5 Haversine Utility — `app/utils/haversine.py`

```python
import math

def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate the great-circle distance between two points on Earth (in km)."""
    R = 6371  # Earth's radius in km

    lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])

    dlat = lat2 - lat1
    dlng = lng2 - lng1

    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
    c = 2 * math.asin(math.sqrt(a))

    return R * c
```

---

## 9. Error Handling & Response Format

### 9.1 Standard Error Response

```json
{
  "detail": "Human-readable error message",
  "error_code": "LOT_NOT_FOUND",
  "field": "quantity_kg"
}
```

### 9.2 HTTP Status Codes Used

| Code | When |
|---|---|
| `200` | Successful read/update |
| `201` | Successful create |
| `400` | Bad request (validation, business rule) |
| `401` | Missing/invalid JWT |
| `404` | Resource not found **OR** unauthorized access (never 403) |
| `409` | Conflict (duplicate phone, etc.) |
| `422` | Pydantic validation error (auto by FastAPI) |
| `500` | Unhandled server error |

### 9.3 Global Exception Handler — `app/middleware/error_handler.py`

```python
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import traceback
import logging

logger = logging.getLogger("agrisense")

class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            logger.error(f"Unhandled error: {e}\n{traceback.format_exc()}")
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"}
            )
```

---

## 10. Security Checklist

| # | Rule | Implementation |
|---|---|---|
| 1 | User ID from JWT only | `get_current_user` dependency — never accept `user_id` from query/body for data access |
| 2 | 404 not 403 | All ownership checks return 404 on failure |
| 3 | Money as integers (paise) | All `_paise` columns are `Integer` — format to ₹ only in frontend |
| 4 | Quantity as integers (kg) | All `_kg` columns are `Integer` |
| 5 | Razorpay webhook signature verification | `razorpay_client.utility.verify_webhook_signature()` on every webhook |
| 6 | Password hashing | `passlib.hash.bcrypt` — never store plaintext |
| 7 | CORS locked down | `allow_origins=["*"]` only in dev; set specific origin in prod |
| 8 | Rate limiting | None for prototype (add in prod with `slowapi`) |
| 9 | SQL injection prevention | SQLAlchemy ORM handles parameterization — no raw SQL |
| 10 | Input validation | Pydantic schemas on every endpoint — reject unexpected fields |

---

## 11. Environment Variables

### `.env.example`

```env
# Database
DATABASE_URL=postgresql+asyncpg://agrisense:agrisense@localhost:5432/agrisense

# JWT
JWT_SECRET=your-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

# Razorpay (test mode)
RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxxxxx
RAZORPAY_KEY_SECRET=xxxxxxxxxxxxxxxxxxxxx

# S3 / MinIO
S3_ENDPOINT=http://localhost:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_BUCKET=agrisense

# Tier 3 (stretch — leave empty until needed)
BHASHINI_API_KEY=
BHASHINI_USER_ID=
AGORA_APP_ID=
AGORA_APP_CERTIFICATE=
```

---

## 12. Docker & Deployment

### `docker-compose.yml`

```yaml
version: "3.9"

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: agrisense
      POSTGRES_PASSWORD: agrisense
      POSTGRES_DB: agrisense
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - miniodata:/data

  backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql+asyncpg://agrisense:agrisense@postgres:5432/agrisense
      S3_ENDPOINT: http://minio:9000
    depends_on:
      - postgres
      - minio
    command: >
      sh -c "alembic upgrade head &&
             uvicorn app.main:app --host 0.0.0.0 --port 8000"

volumes:
  pgdata:
  miniodata:
```

### `Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### `requirements.txt`

```
fastapi==0.115.0
uvicorn[standard]==0.30.0
sqlalchemy[asyncio]==2.0.32
asyncpg==0.29.0
alembic==1.13.2
pydantic-settings==2.4.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
razorpay==1.4.2
boto3==1.35.0
httpx==0.27.0
python-multipart==0.0.9
pytest==8.3.2
pytest-asyncio==0.24.0
httpx==0.27.0
```

### Production Deployment (AWS EC2)

```bash
# On EC2 instance:
git clone <repo> && cd agrisense-backend
cp .env.example .env  # edit with prod values
docker-compose up -d
# Backend available at http://<ec2-ip>:8000
```

---

## 13. Team Ownership & Parallel Work Map

### Module Independence Diagram

```
                          ┌──────────────────────┐
                          │   Shared Scaffold     │
                          │   (Akash builds first)│
                          │                       │
                          │  main.py, config.py   │
                          │  database.py          │
                          │  dependencies/auth.py │
                          │  ALL models/*.py      │
                          │  ALL schemas/*.py     │
                          └─────────┬─────────────┘
                                    │
            ┌───────────┬───────────┼───────────┬──────────────┐
            │           │           │           │              │
            ▼           ▼           ▼           ▼              ▼
     ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
     │  Akash   │ │  Nikhil  │ │  Nilesh  │ │  Kartik  │ │  Shreya  │
     │          │ │          │ │          │ │          │ │  Pranay  │
     │ auth.py  │ │ ai.py    │ │ offers.py│ │ mandi.py │ │ (Frontend│
     │ users.py │ │ price_   │ │ demands  │ │ logistics│ │  only)   │
     │ lots.py  │ │  engine  │ │ .py      │ │ .py      │ │          │
     │ fpo.py   │ │ window_  │ │ transac- │ │ seed_    │ │          │
     │ grading_ │ │  engine  │ │ tions.py │ │ data.py  │ │          │
     │  engine  │ │ matching │ │ disputes │ │          │ │          │
     │          │ │  _engine │ │ .py      │ │          │ │          │
     └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘
```

### Detailed Task Breakdown

#### **Akash** — Scaffold + Auth + Lots + FPO + Grading

| Priority | Task | Files to Create/Edit | Depends On |
|---|---|---|---|
| P0 | Project scaffold, docker-compose, models, schemas | `main.py`, `config.py`, `database.py`, `models/*`, `schemas/*`, `docker-compose.yml` | Nothing |
| P0 | Auth router + service | `routers/auth.py`, `services/auth_service.py`, `dependencies/auth.py` | Scaffold |
| P0 | Users router | `routers/users.py` | Auth |
| P1 | Lots router + service | `routers/lots.py`, `services/lot_service.py` | Auth, Models |
| P1 | Self-assay grading engine | `engines/grading_engine.py` | Nothing (pure logic) |
| P1 | FPO aggregate router | `routers/fpo.py`, `services/fpo_service.py` | Lots, Models |
| P1 | Database migrations | `alembic/versions/*` | Models |

#### **Nikhil** — AI Engines + AI Router

| Priority | Task | Files to Create/Edit | Depends On |
|---|---|---|---|
| P0 | Price engine (load models, predict) | `engines/price_engine.py` | Pre-trained model files |
| P0 | Window + refusal engine | `engines/window_engine.py` | Price engine |
| P1 | Matching engine | `engines/matching_engine.py`, `utils/haversine.py` | Nothing (pure logic) |
| P1 | AI router | `routers/ai.py` | Price engine, Window engine |
| P2 | Generate forecasts script | `scripts/generate_forecasts.py` | Price engine |
| T3 | Voice engine (Bhashini TTS) | `engines/voice_engine.py`, `routers/voice.py` | Bhashini API key |

#### **Nilesh** — Offers + Transactions + Disputes + Deploy

| Priority | Task | Files to Create/Edit | Depends On |
|---|---|---|---|
| P0 | Offers router + service | `routers/offers.py`, `services/offer_service.py` | Auth, Lots model |
| P0 | Demands router + service | `routers/demands.py`, `services/demand_service.py` | Auth |
| P1 | Transactions router + Razorpay | `routers/transactions.py`, `services/transaction_service.py` | Offers, Razorpay keys |
| P1 | Disputes router | `routers/disputes.py`, `services/dispute_service.py` | Transactions |
| P2 | EC2 deployment | `Dockerfile`, deploy script | All services |
| T3 | Call signaling (Agora) | `routers/voice.py` (calls portion) | Agora keys |

#### **Kartik** — Data Layer + Mandi + Logistics

| Priority | Task | Files to Create/Edit | Depends On |
|---|---|---|---|
| P0 | Seed mandi_locations data | `scripts/seed_data.py` | Database schema |
| P0 | Mandi router | `routers/mandi.py` | Mandi model |
| P1 | Logistics router | `routers/logistics.py`, `services/logistics_service.py` | Models, `haversine.py` |
| P1 | Seed demo logistics providers | `scripts/seed_data.py` | Database schema |
| P1 | Seed demo buyer_demand data | `scripts/seed_data.py` | Database schema |
| P2 | Agmarknet data ingestion | Separate script | External API |

#### **Shreya** — Frontend (Farmer Stack)

| Priority | Task | Depends On (Backend) |
|---|---|---|
| P0 | Auth screens | `POST /auth/register`, `POST /auth/login` |
| P1 | Lot creation flow | `POST /lots` |
| P1 | Self-assay grade wizard | `POST /lots/{id}/self-assay` |
| P1 | Sale window / refusal screen | `GET /lots/{id}/price-suggestion` |
| P2 | Match results screen | `GET /lots/{id}/matches` |
| T3 | 🔊 Listen button | `POST /voice/narrate` |

#### **Pranay** — Frontend (Buyer Stack + Shared Components)

| Priority | Task | Depends On (Backend) |
|---|---|---|
| P0 | Shared components (nav, cards, etc.) | None |
| P1 | Demand creation | `POST /demands` |
| P1 | Multi-lot match results | `GET /demands/{id}/matches` |
| P1 | Offer flow | `POST /offers`, `PATCH /offers/{id}` |
| P1 | Payment flow | `POST /transactions/{offer_id}/create-order` |
| P2 | Dispute screen | `POST /disputes` |
| T3 | Call screen (buyer side) | `/calls/initiate` |

### Parallel Work Rules

> **IMPORTANT:**
> 1. **Nobody edits `models/` or `schemas/` after initial scaffold** without announcing it in the group chat. Schema changes affect everyone.
> 2. Each person owns their `routers/<file>.py` and `services/<file>.py` — no one else touches them.
> 3. If you need a utility (haversine, money formatting), check `utils/` first. If it doesn't exist, add it to `utils/` — not inside your router.
> 4. All services accept a `db: AsyncSession` parameter and the `User` object — never create their own sessions.
> 5. Frontend devs (Shreya, Pranay) can start immediately using the Swagger docs at `/docs` — no need to wait for all endpoints.

---

## 14. Testing Strategy

### 14.1 Test Setup — `tests/conftest.py`

```python
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.main import app
from app.database import Base, get_db
from app.dependencies.auth import create_access_token

TEST_DATABASE_URL = "postgresql+asyncpg://agrisense:agrisense@localhost:5432/agrisense_test"

test_engine = create_async_engine(TEST_DATABASE_URL)
TestSession = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

@pytest.fixture(autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def db_session():
    async with TestSession() as session:
        yield session

@pytest.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()

@pytest.fixture
def farmer_token():
    return create_access_token({"user_id": 1, "role": "farmer"})

@pytest.fixture
def buyer_token():
    return create_access_token({"user_id": 2, "role": "buyer"})
```

### 14.2 Run Tests

```bash
# Create test database first:
docker exec -it agrisense-postgres psql -U agrisense -c "CREATE DATABASE agrisense_test;"

# Run all tests:
pytest tests/ -v

# Run specific module:
pytest tests/test_lots.py -v

# Run with coverage:
pytest tests/ --cov=app --cov-report=term-missing
```

### 14.3 What Each Person Tests

| Person | Tests |
|---|---|
| Akash | `test_auth.py`, `test_lots.py`, `test_grading.py` |
| Nikhil | `test_price_engine.py`, `test_window_engine.py`, `test_matching.py` |
| Nilesh | `test_offers.py`, `test_transactions.py`, `test_disputes.py` |
| Kartik | `test_mandi.py`, `test_logistics.py`, `test_seed.py` |

---

## 15. Git Workflow

### Branch Naming

```
main              ← production-ready, deploy from here
├── dev           ← integration branch, all PRs merge here first
├── feat/auth     ← Akash
├── feat/lots     ← Akash
├── feat/ai       ← Nikhil
├── feat/offers   ← Nilesh
├── feat/mandi    ← Kartik
├── feat/payments ← Nilesh
└── ...
```

### Workflow

```bash
# Start a feature:
git checkout dev && git pull
git checkout -b feat/your-feature

# Work, commit often:
git add . && git commit -m "feat(lots): add self-assay endpoint"

# Push and create PR to dev:
git push origin feat/your-feature
# Create PR on GitHub → merge to dev

# Before starting new feature, always:
git checkout dev && git pull
```

### Commit Message Convention

```
feat(scope): description     # new feature
fix(scope): description      # bug fix
refactor(scope): description # code restructure
docs(scope): description     # documentation
test(scope): description     # tests
chore(scope): description    # tooling, deps

Examples:
feat(auth): add JWT refresh endpoint
fix(offers): validate lot ownership before creating offer
refactor(matching): extract scoring into separate function
```

---

## Quick Reference: "I just joined, what do I do?"

1. **Clone** the repo, run `docker-compose up -d postgres minio`
2. **Setup** Python env, install deps, run `alembic upgrade head`
3. **Find your name** in Section 13 — that's your module
4. **Read the API contract** for your endpoints in Section 7
5. **Create your branch**: `git checkout -b feat/<your-module>`
6. **Create your router** in `app/routers/`, your service in `app/services/`
7. **Use `Depends(get_current_user)`** or `Depends(require_role(...))` for auth
8. **Write tests** in `tests/test_<your-module>.py`
9. **Push and PR** to `dev` when ready
10. **Check Swagger** at `http://localhost:8000/docs` to test your endpoints

---

> **Bottom line:** This architecture ensures every teammate has a clearly scoped module with defined interfaces. No one blocks anyone. The shared scaffold (models, auth, config) is built first by Akash, then everyone works in parallel on their own router + service + engine files. Merge to `dev` often, test against Swagger, and integrate end-to-end before the freeze.
