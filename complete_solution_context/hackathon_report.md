# Smart India Hackathon Report: MandiSetu (AgriSense)
**Problem Statement:** PS 26132 — "Strengthening market linkages and price discovery for farmers"

## 1. Problem & Solution Summary
The current agricultural supply chain forces farmers to rely on middlemen, leading to suboptimal price discovery, exploitative holding costs, and a lack of direct market linkages to institutional buyers. This codebase implements **MandiSetu** (also referred to internally as AgriSense), a platform designed to bridge this gap by directly connecting farmers with buyers and FPOs. It provides machine learning-powered price forecasting using Agmarknet data, a deterministic "Window Engine" that recommends whether to sell immediately or hold inventory based on holding costs versus predicted gains, and a secure escrow-based transaction engine to facilitate direct trustless trade.

## 2. Complete Feature Inventory

### Farmer-Side
- **Phone Login & Profile**: Allows farmers to onboard and set preferences. 
  - *Frontend*: `frontend/src/screens/farmer/S02_Phone.tsx`, `S03_Profile.tsx`
  - *Backend*: `app/routers/auth.py` (`POST /otp/request`, `POST /otp/verify`, `POST /register`)
  - *State*: Fully working API, but OTP delivery is mocked (returns in dev response).
- **Create Lot & Self Assay**: Farmers can digitize their inventory and provide a self-assay to generate an assessed grade.
  - *Frontend*: `frontend/src/screens/farmer/S12_CreateLot.tsx`, `S13_SelfAssay.tsx`
  - *Backend*: `app/routers/lots.py` (`POST /lots`, `POST /lots/{lot_id}/assay`, `POST /lots/{lot_id}/photo`)
  - *State*: Fully working.
- **AI Price Forecast & Model Card**: Visualizes future prices (p10/p50/p90) across a time horizon.
  - *Frontend*: `frontend/src/screens/farmer/S07_Forecast.tsx`, `S08_ModelCard.tsx`
  - *Backend*: `app/routers/ai.py` (`GET /forecast`), `app/ml/quantile.py`
  - *State*: Fully working (uses real LightGBM models if generated; otherwise stubs).
- **Verdict & Cost Breakdown (Window Engine)**: Calculates whether to `SELL_NOW`, `HOLD`, `SPLIT`, or gives `NO_ADVICE` based on carrying costs (storage, spoilage) versus potential price appreciation.
  - *Frontend*: `frontend/src/screens/farmer/S09_Verdict.tsx`, `S10_CostBreakdown.tsx`
  - *Backend*: `app/routers/ai.py` (`POST /window/recommend`), `app/engines/window_engine.py`
  - *State*: Fully working.
- **Pledge Loan Quotes**: Calculates loan value against assessed warehouse inventory for farmers choosing to `HOLD`.
  - *Frontend*: `frontend/src/components/farmer/PledgeCard.tsx`
  - *Backend*: `app/engines/window_engine.py` (`compute_pledge_quote`)
  - *State*: Fully working calculation, no actual lending integration.
- **Offers Management**: Farmers can review, accept, reject, or counter buyer offers.
  - *Frontend*: `frontend/src/screens/farmer/S14_CounterOffer.tsx`, `S15_MyLots.tsx`
  - *Backend*: `app/routers/offers.py` (`POST /offers/{offer_id}/accept/reject/counter`)
  - *State*: Fully working.

### Buyer-Side
- **Buyer Login**: Onboarding tailored to institutional buyers.
  - *Frontend*: `frontend/src/screens/buyer/S17_BuyerLogin.tsx`
  - *Backend*: `app/routers/auth.py`
  - *State*: Fully working (OTP is mocked).
- **Post Demand & Matches**: Buyers list their required commodity, quantity, and grade, and the system matches them against farmer lots.
  - *Frontend*: `frontend/src/screens/buyer/S18_PostDemand.tsx`, `S19_Matches.tsx`
  - *Backend*: `app/routers/demands.py` (`POST /demands`, `GET /demands/{demand_id}/matches`)
  - *State*: Fully working.
- **Escrow Timeline**: A shared ledger timeline between buyer and farmer showing transaction progression.
  - *Frontend*: `frontend/src/screens/buyer/S22_EscrowTimeline.tsx`, `frontend/src/components/EscrowTimeline.tsx`
  - *Backend*: `app/routers/transactions.py` (`GET /transactions/{transaction_id}`, `POST /transactions/{transaction_id}/transition`)
  - *State*: Fully working API, but actual money movement is simulated.
- **Buyer Reliability & Data Provenance**: Displays buyer metrics (renegotiation bps, on-time payments) and transparent data origin tracing.
  - *Frontend*: `frontend/src/screens/buyer/S23_BuyerReliability.tsx`, `S24_DataProvenance.tsx`
  - *Backend*: `app/routers/users.py` (`GET /{buyer_id}/reliability`), `app/routers/meta.py` (`GET /data-provenance`)
  - *State*: Fully working.

### FPO-Side
- **Lot Aggregation**: Combine multiple small farmer lots into a single batch lot.
  - *Backend*: `app/routers/lots.py` (`POST /lots/aggregate`)
  - *State*: Backend fully working. No dedicated frontend screens found.

### System/Shared
- **Voice / Assistant**: Audio interactions/translation for accessibility.
  - *Frontend*: `frontend/src/screens/farmer/S28_Assistant.tsx`, `frontend/src/lib/voice.ts`
  - *Backend*: Defined in architecture as Tier 3 (`app/models/voice.py`, `app/routers/voice.py`)
  - *State*: Partially implemented/Stubbed.

## 3. Backend Architecture

### API Endpoints
- **Auth**: `POST /auth/otp/request`, `POST /auth/otp/verify`, `POST /auth/register`, `GET /auth/me`, `POST /auth/locale`
- **Users**: `GET /users/{buyer_id}/reliability`
- **Demands**: `POST /demands`, `GET /demands`, `GET /demands/{demand_id}/matches`
- **Lots**: `POST /lots`, `GET /lots`, `GET /lots/{lot_id}`, `POST /lots/aggregate`, `POST /lots/{lot_id}/assay`, `POST /lots/{lot_id}/photo`, `GET /lots/{lot_id}/price-suggestion`, `GET /lots/{lot_id}/matches`
- **Offers**: `POST /offers`, `GET /offers`, `POST /offers/{offer_id}/accept`, `POST /offers/{offer_id}/reject`, `POST /offers/{offer_id}/counter`, `GET /offers/{offer_id}/thread`
- **Transactions (Escrow)**: `GET /transactions/{transaction_id}`, `POST /transactions/{transaction_id}/transition`
- **AI**: `GET /ai/forecast`, `POST /ai/window/recommend`
- **Meta (Reference)**: `GET /meta/init`, `GET /meta/health`, `GET /meta/data-provenance`, `GET /meta/districts`, `GET /meta/commodities`, `GET /meta/warehouses`, `GET /meta/markets`

### Database Schema (PostgreSQL + PostGIS)
- **Users Layer**: `users` (base profile with PostGIS `geom`), `farmers` (link to FPO), `buyers` (company details, reliability metrics), `fpos`, `otp_codes`
- **Inventory & Markets**: `lots` (farmer inventory), `batch_lot_members` (aggregation mappings), `buyer_demand`
- **Reference Data**: `mandi_locations`, `districts`, `commodities`, `warehouses`, `logistics_cost_routes`
- **Trade & Logistics**: `offers`, `offer_lots`, `transactions`, `escrow_events`, `logistics_providers`, `disputes`
- **AI & Aux**: `price_forecasts`, `pledge_quotes`, `call_sessions`, `voice_interactions`

### External Services Integrated
- **MinIO**: S3-compatible local bucket (`agrisense`) for photos and files. (Live in Docker)
- **Redis**: Caching and Celery Task Queue backend. (Live in Docker)
- **Razorpay**: Referenced in `requirements.txt` and DB fields (`razorpay_order_id` in `transactions`), but actual API implementation is mocked/missing.
- **Bhashini / Agora**: Referenced in config (`BHASHINI_API_KEY`, `AGORA_APP_ID`) for voice/video, but currently stubbed.

## 4. AI/ML Components

### 1. Price Forecast Engine (Actual Machine Learning)
- **What it predicts**: Daily price quantiles (p10, p50, p90) for commodities across a future horizon.
- **Model**: Direct multi-horizon LightGBM quantile models (trained via `scripts/train_and_backtest.py`).
- **Data Source**: Historical snapshot from `app/ml/snapshots/core_series.csv` (Agmarknet data).
- **Location**: `app/ml/quantile.py`, `app/engines/price_engine.py` -> `predict_quantiles()`.

### 2. Window Engine / Verdict (Rule-Based Logic)
- **What it does**: Computes whether the farmer should `SELL_NOW`, `HOLD`, `SPLIT`, or gives `NO_ADVICE`. 
- **Method**: It takes the LightGBM price forecast (p50) and subtracts computed holding costs (storage per kg/day, spoilage %, loading). This is a purely mathematical, deterministic rule engine—**it is not a machine learning model**. 
- **Location**: `app/engines/window_engine.py` and `app/domain/window.py`.

## 5. Frontend Architecture
Built using **React Native** (expo/CLI), intended for mobile cross-platform use, rendering highly specialized functional screens.

- **Stack**: React Native, React Navigation (Bottom Tabs, Native Stack), Tanstack React Query.
- **Farmer Flow**: `AuthStack` (`S02_Phone`, `S03_Profile`) -> `FarmerTabs` -> `S04_Home` -> `S12_CreateLot` -> `S13_SelfAssay`. From the lot, they can access AI features (`S07_Forecast`, `S08_ModelCard`, `S09_Verdict`, `S10_CostBreakdown`) calling `/ai/forecast` and `/ai/window/recommend`. They review offers in `S15_MyLots` and `S14_CounterOffer`.
- **Buyer Flow**: `AuthStack` (`S17_BuyerLogin`) -> `BuyerTabs` -> `S18_PostDemand` (calls `POST /demands`) -> `S19_Matches` -> `S20_LotDetail`. Once agreed, they monitor `S22_EscrowTimeline` (calls `/transactions/{id}`).
- **Key Components**: `ForecastFan.tsx` (renders the p10-p90 forecast cones), `PledgeCard.tsx` (renders loan estimates), `EscrowTimeline.tsx` (renders the transaction progression ladder).

## 6. What's Real vs What's Mocked/Simulated
*This project utilizes a highly functional API scaffold, but uses extensive simulation to bridge third-party dependencies.*

- **Real**:
  - The PostgreSQL + PostGIS database schema, relationships, and queries.
  - The API request parsing, data validation (Pydantic), and endpoint structures.
  - The LightGBM price forecasting pipeline (when run with real pickle files via `scripts/train_and_backtest.py`).
  - The deterministic mathematical calculations for holding costs vs gains in `app/engines/window_engine.py`.
- **Mocked / Simulated**:
  - **OTP Validation**: `app/services/auth_service.py` generates OTPs locally and echoes them in the API response in dev mode. No SMS gateway (e.g., MSG91/Twilio) is actually making network requests.
  - **Payments (Razorpay)**: Despite config flags, the `transactions` state machine simulates payment progression (e.g., `PENDING_BUYER_DEPOSIT` -> `PAID`) without initiating real Razorpay orders.
  - **Fallback ML**: If the LightGBM `.pkl` files are not generated, `app/ml/quantile.py` falls back to `_stub_predict()`, which hallucinates a deterministic 200,000 paise base price with simple linear noise.
  - **Data Population**: Mandis, districts, reference warehouses, logistics providers, and demo farmers/buyers are hard-seeded by `scripts/seed_data.py`. 

## 7. Gaps & Incomplete Areas
- **Bhashini / Agora Integration**: Designated as "Tier 3" in the architecture. Frontend voice logic (`S28_Assistant.tsx`) and database tables (`call_sessions`, `voice_interactions`) exist, but the actual real-time translation pipelines are incomplete.
- **FPO Frontend**: The `/aggregate` endpoint allows combining lots mathematically, but no dedicated frontend screen exists for FPO Admins to use this feature.
- **Dispute Resolution**: `Dispute` tables exist in DB schemas, and `S25_Dispute.tsx` exists on the frontend, but actual mediation logic (who arbitrates, how refunds are processed) is incomplete.

## 8. Tech Stack Summary
*(Verified from actual repo configs: `docker-compose.yml`, `requirements.txt`, `package.json`)*
- **Backend API**: Python 3.11, FastAPI, Uvicorn.
- **Database**: PostgreSQL 15, PostGIS 3.4 (GIS), PgBouncer (Connection Pooling).
- **ORM & Migrations**: SQLAlchemy 2.0 (Async), Alembic, GeoAlchemy2.
- **Background Tasks & Caching**: Redis 7, Celery 5.4.
- **Storage**: MinIO (S3 compatible blob storage).
- **AI/ML**: LightGBM 4.3, Pandas 2.2, Numpy 1.26, Scipy, Joblib.
- **Frontend App**: React Native (0.76.9), TypeScript, React Navigation 7, TanStack React Query 5.
- **Infra**: Docker, Docker Compose, Nginx (Alpine).
