# AgriSense — AI Agents Deployment Vision

> **Document Purpose:** This document captures the complete vision for AI agent deployment in AgriSense — what is currently executed, what is partially built, and what is planned for future iterations. It serves as the single source of truth for the AI/ML deployment roadmap.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [What Is Currently Deployed (Tier 1 & 2)](#2-what-is-currently-deployed-tier-1--2)
3. [Partially Implemented Components](#3-partially-implemented-components)
4. [Future Vision (Tier 3 & Beyond)](#4-future-vision-tier-3--beyond)
5. [Architecture Overview](#5-architecture-overview)
6. [Deployment Infrastructure](#6-deployment-infrastructure)
7. [ML Pipeline & Model Lifecycle](#7-ml-pipeline--model-lifecycle)
8. [Voice AI Deployment](#8-voice-ai-deployment)
9. [Security & Safety Guardrails](#9-security--safety-guardrails)
10. [Roadmap & Milestones](#10-roadmap--milestones)

---

## 1. Executive Summary

AgriSense deploys **modular AI agents** as backend engines that power agricultural commodity trading decisions. The system is built on a **frozen contract architecture** where ML models and decision logic are decoupled, enabling independent iteration.

**Current State:**
- 5 core AI engines deployed and operational
- Real LightGBM quantile regression models for price forecasting
- Rule-based grading and window/refusal decision engines
- Sarvam AI speech-to-text proxy for voice input
- Full ML training pipeline with walk-forward backtesting

**Future Vision:**
- Voice TTS for vernacular narration of sale-window advice
- WebRTC calling with AI negotiation overlay
- Computer vision grading as secondary signal
- Full voice-driven lot creation

---

## 2. What Is Currently Deployed (Tier 1 & 2)

### 2.1 Price Engine (`app/engines/price_engine.py`)

**Status:** ✅ Fully Deployed

**Purpose:** Predicts commodity price quantiles (p10, p50, p90) for the next 14 days using trained LightGBM models.

**Key Components:**
- **Model Loading:** Loads pickled LightGBM models from `app/ml/artifacts/{commodity}.pkl` at startup
- **Feature Engineering:** 40+ backward-looking features (lags, rolling stats, momentum, weather, calendar) — zero future leakage
- **Prediction Interface:** `predict_quantiles(commodity, market, as_of, horizon) → list[(p10, p50, p90)]`
- **Graceful Degradation:** Falls back to synthetic stubs when real models unavailable

**Frozen Contract (`app/ml/quantile.py`):**
```python
def predict_quantiles(commodity, market, as_of, horizon) -> list[tuple[int, int, int]]:
    """Returns daily p10/p50/p90 predictions in integer paise."""
```

**Refusal Handling:** Raises `ModelUnavailable` exception when commodity model not trained — decision lane catches this and returns `NO_ADVICE`.

---

### 2.2 Window + Refusal Engine (`app/engines/window_engine.py` + `app/domain/window.py`)

**Status:** ✅ Fully Deployed

**Purpose:** Transforms price forecasts into actionable sale-window recommendations: `SELL_NOW`, `HOLD`, `SPLIT`, or `NO_ADVICE`.

**Decision Logic:**
1. **Refusal Gate 1:** Insufficient history (< 180 days) → `NO_ADVICE`
2. **Refusal Gate 2:** Model unavailable → `NO_ADVICE`
3. **Refusal Gate 3:** Spot price non-positive → `NO_ADVICE`
4. **Refusal Gate 4:** Band width > 35% at chosen day → `NO_ADVICE`
5. **Refusal Gate 5:** Expected gain below cost floor → `SELL_NOW`
6. **SPLIT Logic:** If p10 scenario worse than sell-now → `SPLIT` (sell half, hold half)
7. **HOLD Logic:** Positive gain with acceptable risk → `HOLD` with optimal hold days

**Cost Computation (`app/domain/costs.py`):**
- Transport cost (per km)
- Commission (2.5%)
- Loading/unloading (per quintal)
- Storage (per kg per day)
- Spoilage estimate (0.2% per day)

**Pledge Quote (`app/domain/pledge.py`):**
- Loan-to-value (LTV) calculation
- Interest computation
- Net benefit analysis
- WDRA warehouse registration check

**Output Contract:**
```python
@dataclass(frozen=True)
class WindowResult:
    action: str                    # SELL_NOW | HOLD | SPLIT | NO_ADVICE
    hold_days: int                 # 0 for SELL_NOW, 1..14 for HOLD/SPLIT
    confidence: str                # low | medium | high
    expected_gain_paise: int       # WHOLE LOT net gain
    worst_case_paise: int          # WHOLE LOT p10 scenario
    refusal_reason: str | None     # Set only when NO_ADVICE
    band_width_bps: int            # (p90 - p10) / p50 × 10000
    itemised_costs: CostBreakdown  # Full cost breakdown
    explain_mr: str                # Marathi one-liner
    explain_en: str                # English one-liner
```

---

### 2.3 Grading Engine (`app/engines/grading_engine.py`)

**Status:** ✅ Fully Deployed

**Purpose:** Deterministic rule engine that maps self-assay answers to crop grades (A/B/C).

**Input:** Farmer answers 6 questions:
- Size uniformity (high/medium/low)
- Color uniformity (high/medium/low)
- Damage percent (0-100)
- Sprouting percent (0-100)
- Moisture level (dry/normal/moist)
- Foreign matter (none/low/moderate/high)

**Scoring:** Each answer maps to 0-3 points, total score determines grade:
- ≥ 80% of max → Grade A
- ≥ 55% of max → Grade B
- < 55% → Grade C

**Output:** Grade label + improvement tip for worst parameter.

---

### 2.4 Matching Engine (`app/engines/matching_engine.py`)

**Status:** ✅ Fully Deployed

**Purpose:** Greedy multi-lot matching between farmer lots and buyer demands.

**Scoring Weights:**
- Grade match: 30%
- Proximity (haversine): 35%
- Price fit: 35%

**Multi-Lot Logic:** For demands exceeding single lot quantity, greedily combines top-ranked lots until demand is covered.

**Async Execution:** Runs as Celery background task when new lot is created.

---

### 2.5 Voice Engine — STT (`app/engines/voice_engine.py`)

**Status:** ✅ Fully Deployed

**Purpose:** Speech-to-text proxy for farmer voice input during registration.

**Architecture Decision:** Server-side proxy (not direct client call) because:
- Sarvam API key never ships on device
- Single place for auth, rate limiting, model swapping
- Supports registration flow (no JWT yet)

**Upstream Contract:**
- Endpoint: `https://api.sarvam.ai/speech-to-text`
- Model: `saaras:v3`
- Audio limit: ≤30s clips
- Languages: Marathi (`mr-IN`), Hindi (`hi-IN`), English (`en-IN`)

**Graceful Degradation:** Returns HTTP 503 when `SARVAM_API_KEY` not configured.

---

### 2.6 ML Training Pipeline (`app/ml/`)

**Status:** ✅ Fully Deployed

**Components:**
- **Training (`train.py`):** Direct multi-horizon LightGBM training
- **Backtesting (`backtest.py`):** Walk-forward evaluation with MASE + coverage metrics
- **Features (`features.py`):** 40+ backward-looking features, zero future leakage
- **Model Card (`model_card.py`):** Provenance metadata generation
- **Walk-forward Export (`walkforward_export.py`):** JSON export of evaluation points

**Model Artifacts:**
- Location: `app/ml/artifacts/{commodity}.pkl`
- Format: Joblib pickle with bundled model dict
- Contents: Models per horizon per quantile, feature names, mappings

---

## 3. Partially Implemented Components

### 3.1 Disputes Router (`app/routers/disputes.py`)

**Status:** 🚧 Stub

**Current State:** Endpoint skeleton exists with TODO comment:
```python
# TODO: Nilesh implements these endpoints
```

**Planned:** Full dispute lifecycle (create, list, resolve) with role-based access.

---

### 3.2 Logistics Router (`app/routers/logistics.py`)

**Status:** 🚧 Stub

**Current State:** Endpoint skeleton exists with TODO comment.

**Planned:** Nearby logistics provider search with haversine filtering.

---

### 3.3 Mandi Router (`app/routers/mandi.py`)

**Status:** 🚧 Stub

**Current State:** Endpoint skeleton exists with TODO comment.

**Planned:** Mandi location listing with district filtering.

---

### 3.4 Transactions Service (`app/services/transaction_service.py`)

**Status:** 🚧 Partial

**Current State:** Basic structure with TODO for access control check.

**Planned:** Full Razorpay integration with webhook handling.

---

## 4. Future Vision (Tier 3 & Beyond)

### 4.1 Voice TTS — Sale-Window Narration

**Status:** 📋 Planned

**Vision:** Read sale-window advice aloud in farmer's preferred language.

**Architecture:**
```
Sale-window advice text (from Window Engine)
        │
        ▼
Translate to farmer's preferred_language
        │
        ▼
Text-to-Speech via Bhashini (primary) / Sarvam (alt) / Google Cloud TTS (fallback)
        │
        ▼
Audio returned to app, played on "🔊 Listen" button
```

**Why This Matters:**
- Vernacular support for non-literate farmers
- Government API (Bhashini) alignment for SIH demo
- ~2-3 hours to implement

**Current Status:** Frontend already has on-device TTS (`speakText`) for dynamic text and pre-generated clips for static phrases. Server TTS is deferred.

---

### 4.2 Call Signaling / WebRTC

**Status:** 📋 Planned

**Vision:** Voice-only calls between farmer and buyer during negotiation.

**Architecture:**
- Managed SDK: Agora, ZegoCloud, or 100ms (free tiers, React Native support)
- Backend issues session token on call initiation
- Both parties join voice-only room
- Call metadata logged in `call_sessions` table

**AI Negotiation Overlay:**
- **NOT** live audio ML (too risky)
- **INSTEAD:** Sale-window band + current offer price shown as persistent overlay
- Farmer sees: "Fair band: ₹1900-2200, Current offer: ₹1950"

**Database Tables (Tier 3):**
```sql
call_sessions(id, offer_id, farmer_user_id, buyer_user_id,
              provider_session_id, status, started_at, ended_at)
voice_interactions(id, user_id, audio_ref, transcript, language,
                    intent_detected, created_at)
```

---

### 4.3 Photo CV Grading

**Status:** 📋 Planned (Tier 2 in original plan)

**Vision:** Computer vision as secondary grading signal alongside self-assay.

**Current Decision:** NOT part of prototype grading decision.
- Domain mismatch with fresh/rotten datasets
- Training data requirements too high for timeline
- Photo stored as buyer-facing evidence only

**Future Implementation:**
- Separate CV model for quality assessment
- Combined score: 70% self-assay + 30% CV
- Requires curated agricultural dataset

---

### 4.4 Full Voice-Driven Lot Creation

**Status:** 📋 Planned (Stretch)

**Vision:** STT → intent parsing → form fill for lot creation.

**Why Deferred:**
- Audio quality issues in field environments
- Background noise handling
- Language detection complexity
- Worse time trade than TTS narration

**Future Architecture:**
```
Farmer speaks → STT transcription → Intent extraction → Form field population → Confirmation
```

---

### 4.5 AI Negotiation Coach

**Status:** 📋 Planned (Stretch, Replaced by Overlay)

**Original Vision:** Real-time AI coaching during calls.

**Replaced By:** Persistent price band overlay (lower risk, similar value).

**Reasoning:**
- Live audio ML is high risk for demo
- Overlay delivers "informed negotiation" value
- No audio processing latency issues

---

## 5. Architecture Overview

### Layer Separation Convention

| Layer | Responsibility | Rule |
|-------|---------------|------|
| **Routers** | HTTP concerns only | Parse request → call service → return response |
| **Services** | Business logic | Accept `db: AsyncSession` + `User`, never raw SQL |
| **Engines** | AI/ML logic | Pure computation, no DB/HTTP |
| **Domain** | Pure decision logic | No side effects, no DB, no HTTP |
| **Models** | Data (SQLAlchemy) | Pure ORM, no business logic |
| **Schemas** | Validation (Pydantic) | Request/response contracts |

### Frozen Contract Pattern

The ML lane and decision lane communicate through a frozen contract:

```python
# app/ml/_contract.py — TypedDicts defining exact field contracts
# Person A (ML) produces → Person B (Decision) consumes
```

**Benefit:** ML models can be retrained without touching decision logic.

---

## 6. Deployment Infrastructure

### Docker Compose Stack

| Service | Image | Purpose |
|---------|-------|---------|
| `postgis` | postgis/postgis:15-3.4-alpine | PostgreSQL with PostGIS |
| `pgbouncer` | edoburu/pgbouncer | Connection pooling |
| `redis` | redis:7-alpine | Caching + Celery broker |
| `minio` | minio/minio | S3-compatible file storage |
| `nginx` | nginx:alpine | Reverse proxy |
| `api` | custom (FastAPI) | Main backend |
| `celery_worker` | custom | Background tasks |

### Startup Sequence

1. FastAPI lifespan handler starts
2. Redis cache initialized via `fastapi-cache2`
3. Price engine loads LightGBM pickles from `app/ml/artifacts/*.pkl`
4. If no models exist, falls back to synthetic stubs
5. Routers registered, server ready

### Production Deployment

- Single AWS EC2 instance via docker-compose
- All Tier 1/2 services on one machine
- Tier 3 services (Bhashini, Agora) are external managed APIs

---

## 7. ML Pipeline & Model Lifecycle

### Training Pipeline

```
Raw Data (Agmarknet)
        │
        ▼
Feature Engineering (40+ features)
        │
        ▼
Walk-Forward Training (LightGBM)
        │
        ▼
Model Validation (MASE + Coverage)
        │
        ▼
Model Card Generation
        │
        ▼
Artifact Export ({commodity}.pkl)
```

### Model Card Metadata

```json
{
  "commodity": "Onion",
  "market": "Lasalgaon APMC",
  "training_date": "2026-09-05",
  "horizon_days": 14,
  "quantiles": [0.10, 0.50, 0.90],
  "metrics": {
    "mase": 0.85,
    "coverage_80": 0.82
  },
  "feature_importance": {...}
}
```

### Inference Pipeline

```
API Request
        │
        ▼
Feature Derivation (from snapshot CSV)
        │
        ▼
Model Lookup (by commodity)
        │
        ▼
Quantile Prediction (p10, p50, p90 per day)
        │
        ▼
Response (list of daily predictions)
```

---

## 8. Voice AI Deployment

### Current: STT Only

**Endpoint:** `POST /api/v1/voice/transcribe`

**Flow:**
1. Mobile app records audio clip
2. POST to backend with audio file + locale
3. Backend proxies to Sarvam STT API
4. Returns transcript + language code

**Why Unauthenticated:**
- Runs during registration (before JWT exists)
- Rate limiting by IP (not per-user)
- Frontend attaches Bearer token only when available

### Future: TTS Narration

**Endpoint:** `POST /api/v1/voice/narrate` (Planned)

**Flow:**
1. Frontend requests narration of sale-window advice
2. Backend translates text to farmer's language
3. Backend calls Bhashini/Sarvam TTS API
4. Returns audio URL for playback

### Future: Call Signaling

**Endpoint:** `POST /api/v1/calls/initiate` (Planned)

**Flow:**
1. Either party taps "Call" during negotiation
2. Backend creates `call_sessions` row
3. Backend issues Agora/ZegoCloud token
4. Both apps join voice room
5. Overlay shows sale-window band + current offer

---

## 9. Security & Safety Guardrails

### Current Guardrails

| Guardrail | Implementation |
|-----------|---------------|
| **API Key Isolation** | Sarvam key server-side only, never on device |
| **Graceful Degradation** | All engines fall back to stubs when models unavailable |
| **Refusal Gates** | Window engine refuses with NO_ADVICE when uncertainty too high |
| **Frozen Contract** | ML/Decision lanes decoupled, validated interface |
| **No Float Currency** | All money fields in integer paise |
| **Input Validation** | Pydantic schemas on every endpoint |

### Future Guardrails

| Guardrail | Implementation |
|-----------|---------------|
| **Rate Limiting** | Per-IP for voice endpoints (currently none) |
| **Audio Size Limits** | Enforce ≤30s clips for STT |
| **Call Authentication** | JWT required for call initiation |
| **TTS Caching** | Cache generated audio to reduce API costs |

---

## 10. Roadmap & Milestones

### Phase 1: Core AI (✅ Complete)

- [x] Price Engine with LightGBM models
- [x] Window + Refusal Engine
- [x] Grading Engine (self-assay)
- [x] Matching Engine (multi-lot)
- [x] Voice STT (Sarvam proxy)
- [x] ML Training Pipeline
- [x] Walk-forward Backtesting

### Phase 2: Platform Completion (🚧 In Progress)

- [ ] Disputes Router (stub → full)
- [ ] Logistics Router (stub → full)
- [ ] Mandi Router (stub → full)
- [ ] Transactions Service (partial → full)
- [ ] Razorpay Integration (test mode)

### Phase 3: Voice & Calling (📋 Planned)

- [ ] Voice TTS Narration (Bhashini/Sarvam)
- [ ] Call Signaling (Agora/ZegoCloud)
- [ ] AI Negotiation Overlay
- [ ] Call Session Logging

### Phase 4: Advanced AI (📋 Stretch)

- [ ] Photo CV Grading (secondary signal)
- [ ] Full Voice-Driven Lot Creation
- [ ] Multi-language Intent Parsing
- [ ] Real-time Market Alerts

---

## Appendix A: Key Files Reference

| File | Purpose |
|------|---------|
| `app/engines/price_engine.py` | Price forecast engine |
| `app/engines/window_engine.py` | Sale-window computation |
| `app/engines/grading_engine.py` | Self-assay grading |
| `app/engines/matching_engine.py` | Multi-lot matching |
| `app/engines/voice_engine.py` | Sarvam STT proxy |
| `app/domain/window.py` | Pure decision logic |
| `app/domain/costs.py` | Cost computation |
| `app/domain/pledge.py` | Pledge quote logic |
| `app/ml/quantile.py` | Frozen ML contract |
| `app/ml/train.py` | Training pipeline |
| `app/ml/backtest.py` | Walk-forward evaluation |
| `app/ml/features.py` | Feature engineering |
| `app/routers/voice.py` | Voice API endpoints |
| `app/schemas/voice.py` | Voice request/response schemas |

---

## Appendix B: Environment Variables

```env
# ML Configuration
ML_ARTIFACT_DIR=app/ml/artifacts
ML_SNAPSHOT_DIR=app/ml/snapshots

# Voice (Sarvam)
SARVAM_API_KEY=your-key-here
SARVAM_ASR_ENDPOINT=https://api.sarvam.ai/speech-to-text
SARVAM_ASR_MODEL=saaras:v3

# Voice (Bhashini - Future TTS)
BHASHINI_API_KEY=
BHASHINI_USER_ID=

# Call Signaling (Future)
AGORA_APP_ID=
AGORA_APP_CERTIFICATE=
```

---

*Document generated: 2026-09-06*
*Repository: AgriSense Backend (SIH PS 26132)*
*Status: Living document — update as deployment evolves*
