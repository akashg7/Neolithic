# NLP Execution Plan: Krishi-Mitr Agentic AI, RAG & Farmer-Side Integration

> **Document Purpose:** End-to-end parallel execution blueprint for a **5-person team** integrating the **Krishi-Mitr** farmer experience with the **FastAPI** backend, building an app-wide **Conversational + Voice AI Agent**, and implementing a rigorous **Chunking, Embedding & RAG Evaluation Pipeline** for NLP assessment.

---

## Table of Contents
1. [Architectural Vision & Core Principles](#1-architectural-vision--core-principles)
2. [Current Codebase Baseline & Gaps to Close](#2-current-codebase-baseline--gaps-to-close)
3. [Team Topology & Parallel Ownership Matrix (5 Members)](#3-team-topology--parallel-ownership-matrix-5-members)
4. [Phase 0: Frozen Inter-Team Contracts (Day 0 — Mandatory Before Splitting)](#4-phase-0-frozen-inter-team-contracts-day-0--mandatory-before-splitting)
5. [Track A — Member 1: UI/UX Fixes & App-Wide Chatbot Interface](#5-track-a--member-1-uiux-fixes--app-wide-chatbot-interface)
6. [Track B — Members 2 & 3: Backend Hardening & Krishi-Mitr Farmer Integration](#6-track-b--members-2--3-backend-hardening--krishi-mitr-farmer-integration)
7. [Track C — Members 4 & 5: Agentic AI, Chunking, Embeddings & Vector DB](#7-track-c--members-4--5-agentic-ai-chunking-embeddings--vector-db)
8. [Phased Execution Timeline & Parallel Milestones](#8-phased-execution-timeline--parallel-milestones)
9. [Integration, Testing & Verification Checklist](#9-integration-testing--verification-checklist)
10. [NLP Evaluator Defense & Benchmark Playbook](#10-nlp-evaluator-defense--benchmark-playbook)

---

## 1. Architectural Vision & Core Principles

### High-Level System Architecture

```
┌────────────────────────────────────────────────────────────────────────────┐
│                  Krishi-Mitr Farmer App (React Native + Web)               │
│  [Onboarding S01-S03]  [Home S04]  [Market/Prices]  [MyLots]  [Deals]      │
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  Persistent Floating Agent Overlay (Text + Voice + Screen Context)   │  │
│  │  • Mounted globally in FarmerRoot / AuthStack                        │  │
│  │  • Renders Action Cards (Verdict, Lot Draft, Forecast) & Deep Links  │  │
│  └───────────────────────────────┬──────────────────────────────────────┘  │
└──────────────────────────────────┼─────────────────────────────────────────┘
                                   │ HTTPS / JWT (REST)
                                   ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                        FastAPI Backend (/api/v1)                           │
│                                                                            │
│  ┌──────────────────────┐    ┌──────────────────────┐    ┌──────────────┐  │
│  │   /voice/* Proxy     │    │    /agent/chat       │    │ Core Farmer  │  │
│  │  Sarvam STT & TTS    │───▶│  Native Tool-Calling │◀──▶│  APIs (Auth, │  │
│  │  (saaras:v3, bulbul) │    │  Agent (Gemini Flash)│    │  Lots, AI,   │  │
│  └──────────────────────┘    └──────────┬───────────┘    │  Prices,Ref) │  │
│                                         │                └──────┬───────┘  │
│                      ┌──────────────────┴──────────────────┐    │          │
│                      ▼                                     ▼    ▼          │
│       ┌──────────────────────────────┐      ┌───────────────────────────┐  │
│       │   RAG Knowledge Tool         │      │ Deterministic Action Tools│  │
│       │  • Query Rewrite / HyDE      │      │ • price_engine (LightGBM) │  │
│       │  • BGE-M3 / Gemini Embeds    │      │ • window_engine (Decision)│  │
│       │  • Qdrant Hybrid Vector DB   │      │ • grading_engine (Assay)  │  │
│       │    (Schemes, Grading, FAQ)   │      │ • lot_service (CRUD)      │  │
│       └──────────────────────────────┘      └───────────────────────────┘  │
│                                                                            │
│  ┌─────────────────────────┐   ┌───────────────────────┐   ┌────────────┐  │
│  │ PostgreSQL 15 + PostGIS │   │  Redis 7 (Cache +     │   │  Celery    │  │
│  │ (Users, Lots, Prices)   │   │  Session Memory + MQ) │   │  Workers   │  │
│  └─────────────────────────┘   └───────────────────────┘   └────────────┘  │
└────────────────────────────────────────────────────────────────────────────┘
```

### Non-Negotiable Architectural Rules
1. **Strict Separation of Numbers vs. Text:**
   * **PostgreSQL + ML Engines (`price_engine`, `window_engine`)** handle all live market prices, $p_{10}/p_{50}/p_{90}$ forecasts, net profit math, and transactional records via **Agent Tool Calls**.
   * **Vector Database (Qdrant)** stores **only unstructured/semi-structured domain knowledge** (government schemes, WDRA loan rules, AGMARK grading guides, post-harvest curing, platform Escrow/Pool explanations, and Marathi/Hindi agricultural glossaries).
   * *Never store live prices or user lot rows in the Vector DB.*
2. **Zero-Hallucination & Safety Guardrail:**
   * If `window_engine` returns `NO_ADVICE` (forecast uncertainty > 35%), the Agent must explain why it cannot advise holding—it must never invent price predictions.
   * No ungrounded chemical/pesticide prescriptions.
3. **Key Security:**
   * Zero API keys (Sarvam, Gemini/OpenAI, Qdrant) in `Krishi-Mitr` frontend code. All external AI and voice calls pass through FastAPI.
4. **Canonical Units & Integer Money:**
   * Backend DB stores prices in **integer paise** and weights in **integer kg/qtl**. Agent tool wrappers convert colloquial farmer units (*1 Bori = 50 kg*, *1 Quintal = 100 kg*, *1 Ton = 1000 kg*) before calling domain services.

---

## 2. Current Codebase Baseline & Gaps to Close

Before splitting into tracks, every member must understand the exact current state of the repository:

| Layer | File / Module | Current State | Action Required |
| :--- | :--- | :--- | :--- |
| **Frontend Config** | `Krishi-Mitr/src/config.ts` | `USE_FIXTURES = true`; hardcoded offline scenario. | Support live `API_BASE_URL` toggle + dev/prod environments. |
| **Frontend API Client** | `Krishi-Mitr/src/lib/api.ts` | 100% static mock fixture layer; direct Sarvam calls on lines 450/498. | Build real HTTP client with JWT attachment; proxy voice through FastAPI. |
| **Frontend Voice** | `Krishi-Mitr/src/lib/voiceService.ts` | Reads client-side `SARVAM_API_KEY` or falls back to Web Speech. | Route TTS to `/api/v1/voice/narrate` with Web Speech offline fallback. |
| **Assistant Screen** | `Krishi-Mitr/src/screens/farmer/S28_Assistant.tsx` | Static 12-question accordion FAQ tucked in hamburger menu. | Upgrade into full conversational view + add persistent floating chatbot across all Farmer screens. |
| **Backend Auth/Lots/AI** | `app/routers/*.py`, `app/services/lot_service.py` | Working endpoints, but `lot_service` & `prices.py` expect integer IDs while frontend uses string IDs (`cmd_onion`, `mkt_lasalgaon`). | Add ID/slug normalization layer (`cmd_onion` ↔ DB `id`) across backend endpoints. |
| **Backend Prices** | `app/routers/prices.py` | `/nearby` uses hardcoded mock prices (`gross = 250000`, `distance_km = 45`). | Replace with real `PriceObservation` + `MandiLocation` Haversine + `LogisticsCostRoute` queries. |
| **Backend Redis Cache** | `app/main.py`, `app/routers/mandi.py` | Redis initialized, but only stub `/mandi.py` uses `@cache` (and isn't mounted in `main.py`). | Add `@cache` to `ref.py` (`/districts`, `/commodities`, `/markets`) and `prices.py`. |
| **Backend Voice DB** | `app/models/voice.py` | `VoiceInteraction.intent_detected` column exists but is never written. | Populate `intent_detected`, transcript, and session logs from Agent & Voice flows. |
| **Agent / RAG Engine** | *(Does not exist yet)* | Only `nlp.md` architectural blueprint exists. | Build Qdrant ingestion pipeline, RAG retrieval, `agent_engine.py`, and evaluation suite. |

---

## 3. Team Topology & Parallel Ownership Matrix (5 Members)

| Member | Role & Track | Owned Directories / Files | Can Work Independently From Day 1? |
| :--- | :--- | :--- | :--- |
| **Member 1** | **Frontend UI/UX & Chatbot UI Engineer** | `Krishi-Mitr/src/components/chat/*`, `Krishi-Mitr/src/screens/farmer/*`, `Krishi-Mitr/src/navigation/*`, `Krishi-Mitr/src/i18n/*` | **Yes** — develops against mock `AgentChatResponse` matching Phase 0 JSON contract. |
| **Member 2** | **Backend Core, DB & Cache Engineer** | `app/routers/ref.py`, `app/routers/prices.py`, `app/routers/lots.py`, `app/services/*`, `app/models/*`, `docker-compose.yml` | **Yes** — hardens APIs, fixes ID resolution, real `/prices/nearby`, Redis caching, adds Qdrant container. |
| **Member 3** | **Krishi-Mitr Farmer Integration Engineer** | `Krishi-Mitr/src/lib/api.ts`, `Krishi-Mitr/src/lib/agentApi.ts`, `Krishi-Mitr/src/lib/voiceService.ts`, `Krishi-Mitr/src/lib/auth.tsx`, `Krishi-Mitr/src/config.ts` | **Yes** — wires screens (`S01`–`S38`) to FastAPI OpenAPI contracts and builds offline fallback toggle. |
| **Member 4** | **NLP Data, Chunking, Embeddings & Eval Engineer** | `data/rag_corpus/*`, `scripts/ingest_rag.py`, `app/rag/*`, `eval/*` | **Yes** — builds corpus, chunkers, BGE-M3/Gemini embeddings, Qdrant indexing, and evaluation notebooks. |
| **Member 5** | **Agentic AI & Tool Orchestration Engineer** | `app/engines/agent_engine.py`, `app/agents/*`, `app/routers/agent.py`, `app/schemas/agent.py` | **Yes** — builds tool-calling LLM loop, Redis session memory, tool wrappers, and UI action emitters. |

---

## 4. Phase 0: Frozen Inter-Team Contracts (Day 0 — Mandatory Before Splitting)

All 5 members must agree on these **3 contracts** in a 60-minute kickoff before writing code. Once frozen, nobody blocks anyone else.

### Contract 1: Agent Chat API (`POST /api/v1/agent/chat` & `POST /api/v1/agent/voice-chat`)

**Request (`AgentChatRequest`):**
```json
{
  "session_id": "sess_f102_98a1",
  "message": "माझ्याकडे १० बोरी कांदा आहे, लासलगावला कधी विकू?",
  "locale": "mr",
  "screen_context": {
    "current_screen": "S04_Home",
    "active_commodity_id": "cmd_onion",
    "active_market_id": "mkt_lasalgaon",
    "active_lot_id": null
  },
  "include_audio": false
}
```
*(Note: `POST /api/v1/agent/voice-chat` accepts `multipart/form-data` with `audio` file + `session_id` + `locale` + `screen_context` JSON string, running `STT -> Agent -> Optional TTS` in a single network round-trip for rural mobile networks.)*

**Response (`AgentChatResponse`):**
```json
{
  "session_id": "sess_f102_98a1",
  "transcript": "माझ्याकडे १० बोरी कांदा आहे, लासलगावला कधी विकू?",
  "intent_detected": "SALE_WINDOW",
  "reply_text": "तुमच्या ५०० किलो कांद्यासाठी लासलगाव मंडीत ५ दिवस थांबण्याचा सल्ला आहे. अंदाजे निव्वळ नफा ₹१,८५० होऊ शकतो (वाहतूक व साठवणूक खर्च वजा करून). सर्वात वाईट परिस्थितीतही ₹४०० नफा राहील.",
  "audio_base64": null,
  "cards": [
    {
      "type": "WINDOW_VERDICT",
      "data": {
        "action": "HOLD",
        "hold_days": 5,
        "expected_gain_paise": 185000,
        "worst_case_paise": 40000,
        "commodity": "Onion",
        "mandi": "Lasalgaon APMC",
        "quantity_kg": 500
      }
    }
  ],
  "ui_action": {
    "type": "OFFER_NAVIGATION",
    "target_screen": "S9_Verdict",
    "cta_label": "संपूर्ण तपशील पहा",
    "params": { "commodity_id": "cmd_onion", "market_id": "mkt_lasalgaon", "qty_kg": 500 }
  },
  "citations": [
    { "source": "window_engine_v1", "title": "14-Day LightGBM Quantile Forecast" }
  ],
  "quick_replies": [
    "५०० किलो कांद्याचा लॉट तयार करा",
    "साठवणूक खर्च किती येईल?",
    "कर्ज (Pledge Loan) मिळेल का?"
  ]
}
```

### Contract 2: Reference ID Resolution Rule
* Frontend continues using canonical strings (`cmd_onion`, `mkt_lasalgaon`, `dist_nashik`) **OR** integer DB IDs (`1`, `2`).
* Backend services accept **both** seamlessly via a shared helper `app/utils/id_resolver.py` (mapping `cmd_onion` $\leftrightarrow$ `Commodities.id`, `mkt_lasalgaon` $\leftrightarrow$ `MandiLocation.id`, `dist_nashik` $\leftrightarrow$ `District.id`).

### Contract 3: Error Envelope
All backend routes—including `/agent/chat`—must strictly return the canonical error format defined in `app/main.py`:
```json
{
  "error": {
    "code": "RATE_LIMITED | UNAUTHENTICATED | SERVICE_UNAVAILABLE",
    "message": "Human-readable message",
    "field": null
  }
}
```

---

## 5. Track A — Member 1: UI/UX Fixes & App-Wide Chatbot Interface

**Owner:** Member 1 (Frontend UI/UX Engineer)  
**Target Directory:** `Krishi-Mitr/src/`

### 5.1 UI/UX Audit & Fixes (Farmer Side)
1. **Unify Visual Polish & Responsive Web/Mobile Layout:**
   * Audit all Farmer screens in `Krishi-Mitr/src/screens/farmer/` (`S00_Splash` through `S38_Notifications`) across both Android (`react-native`) and Web (`react-native-web` at `8080`) viewports.
   * Fix overflow/clipping in Marathi (`mr`) and Hindi (`hi`) strings (Devanagari line-height and `fontFamily` tokens in `src/theme/tokens.ts`).
   * Ensure consistent header/safe-area spacing (`SCREEN_BG = '#FAF6EE'`) across `FarmerTabs.tsx` and nested stack screens (`S09_Verdict`, `S15_MyLots`, `S22_PricePublish`, `S27_Bargaining`).
   * Fix empty/loading/error states (`Skeleton.tsx`, `EmptyState.tsx`, `ErrorState.tsx`) when switching from instant static fixtures to async network calls.
   * Verify compliance with project UI invariants: **zero emojis**, equal font sizing for expected gain and worst-case risk (`S09_Verdict`), and honest `SourceBadge` rendering (`AGMARKNET`, `IMPUTED`, `SYNTHETIC`).

### 5.2 Persistent App-Wide Chatbot Feature
1. **Create Global `AgentContext` (`src/lib/agentContext.tsx`):**
   * Tracks `isOpen`, `messages[]`, `sessionId`, `isRecording`, `isThinking`, and `currentScreenContext` (current route name, selected `commodity_id`, `market_id`, `lot_id`).
   * Hooks into `navigationRef.ts` (`onStateChange`) so the chatbot **automatically knows which screen the farmer is looking at**.
2. **Build Persistent Floating Widget (`src/components/chat/FloatingAssistant.tsx`):**
   * Mount once inside `FarmerRoot` (`RootNavigator.tsx`) and optionally on `AuthStack` (`S02_Phone`, `S03_Profile` for onboarding help).
   * Floating terracotta/green mic+chat pill positioned cleanly above the bottom tab bar (`FarmerTabs`) without blocking primary CTAs.
   * Tapping opens a sleek **Slide-Up Bottom Sheet / Modal (`src/components/chat/ChatDrawer.tsx`)**:
     * **Voice-First Input:** Press-and-hold or tap-to-record button (reusing `VoiceMic.tsx` recording logic) + text input box for typing.
     * **Audio Replay ("Listen" Speaker Icon):** Plays `audio_base64` from backend or falls back to `voiceService.speak()` per assistant bubble.
     * **Rich Interactive Action Cards (`src/components/chat/ChatCards.tsx`):**
       * `WINDOW_VERDICT` card (shows `HOLD/SELL/NO_ADVICE` + Gain vs Worst-Case side-by-side).
       * `PRICE_SNAPSHOT` card (today's modal rate + 7-day trend arrow).
       * `LOT_DRAFT` card (pre-filled Commodity, Quantity in kg, Mandi + `"Confirm & Publish"` button).
       * `RAG_CITATION` chips (collapsible *"Source: WDRA Guidelines / NHRDF Storage Manual"* badge—great for evaluators!).
     * **Deep-Link Navigation:** Tapping a `ui_action` button closes/minimizes the drawer and navigates directly to the target screen (`S9_Verdict`, `S15_MyLots`, `S13_CropLoan`, etc.) using `navigationRef.ts`.
     * **Context-Aware Quick Prompts (`quick_replies`):** Dynamic 1-tap Marathi/Hindi suggestion chips based on the current screen (e.g., on `S20_QualityDiagnostic`, show *"ग्रेड A कसा मिळवायचा?"*).
3. **Upgrade `S28_Assistant.tsx`:**
   * Convert `S28_Assistant.tsx` from static accordions into the **Full-Screen Assistant & Quick Guides** page (embedding the live `ChatDrawer` conversation alongside quick starter topic cards mapped to RAG queries).

---

## 6. Track B — Members 2 & 3: Backend Hardening & Krishi-Mitr Farmer Integration

### 6.1 Member 2: Backend Hardening, Real Queries, Cache & Infra
**Target Directory:** `app/`, `docker-compose.yml`, `alembic/`

1. **Docker & Vector DB Infrastructure (`docker-compose.yml`):**
   * Add **`qdrant`** service (`qdrant/qdrant:latest`, ports `6333:6333`, `6334:6334`, persistent volume `qdrantdata:/qdrant/storage`).
   * Add environment variables in `app/config.py` and `.env.example`: `LLM_PROVIDER`, `GEMINI_API_KEY` (or `OPENAI_API_KEY`), `QDRANT_URL`, `QDRANT_COLLECTION`, `EMBEDDING_MODEL`.
2. **Canonical ID Resolver (`app/utils/id_resolver.py`):**
   * Build async/cached resolver mapping frontend string IDs (`cmd_onion`, `mkt_lasalgaon`, `dist_nashik`) and integer IDs (`1`, `2`, `3`) cleanly across `lots.py`, `prices.py`, `ref.py`, and `ai.py`.
3. **Fix Stubbed & Missing Farmer Endpoints:**
   * **`app/routers/prices.py` (`/prices/nearby`):** Replace hardcoded `gross = 250000` mock loop with real PostgreSQL queries joining `MandiLocation`, latest `PriceObservation`, `LogisticsCostRoute` (or `haversine_km` fallback), sorted descending by `net_paise_per_qtl`.
   * **`app/routers/ref.py`:** Ensure `/districts`, `/commodities`, `/markets` (`/mandis`), `/warehouses` return canonical fields (`id`, `slug_id`, `name`, `name_mr`, `lat`, `lon`).
   * **`app/routers/lots.py` & `app/services/lot_service.py`:** Verify `POST /lots`, `GET /lots`, `POST /lots/{id}/assay`, and `GET /lots/{id}/price-suggestion` handle both `qty_kg` and `quantity_qtl` and auto-trigger `price_engine` + `window_engine`.
4. **Apply Redis Caching Where It Matters:**
   * Mount/apply `@cache(expire=3600)` on `ref.py` (`/districts`, `/commodities`, `/markets`, `/warehouses`).
   * Apply `@cache(expire=300)` on `prices.py` (`/series`, `/nearby`) and `ai.py` (`/forecast`) keyed by query parameters.
   * Create a simple benchmark script `scripts/benchmark_redis.py` measuring P50/P99 latency and RPS with cache bypassed vs. enabled.
5. **Audit & Chat Logging Schema:**
   * Extend `VoiceInteraction` (or add `AgentTurnLog` table via Alembic migration) in `app/models/voice.py` to log `session_id`, `user_id`, `screen_context`, `transcript`, `intent_detected`, `tools_called` (JSONB), `rag_sources` (JSONB), `latency_ms`, and `created_at`.

### 6.2 Member 3: Krishi-Mitr Farmer-Side Integration
**Target Directory:** `Krishi-Mitr/src/lib/`, `Krishi-Mitr/src/config.ts`, `Krishi-Mitr/api/`

1. **Configurable Live Mode (`Krishi-Mitr/src/config.ts`):**
   * Replace hardcoded `export const USE_FIXTURES = true;` with environment-aware configuration (`API_BASE_URL` pointing to FastAPI `/api/v1` in dev/prod, with `USE_FIXTURES` kept strictly as an explicit offline/demo fallback toggle).
2. **Real HTTP Client Layer (`Krishi-Mitr/src/lib/httpClient.ts` & `api.ts`):**
   * Refactor `Krishi-Mitr/src/lib/api.ts` so every Farmer endpoint switches cleanly between live `fetch()` and fixtures when `USE_FIXTURES` is toggled:
     * **Auth:** `requestOtp()`, `verifyOtp()`, `registerFarmer()`, `getMe()`, `updateLocale()`. Store JWT in `AsyncStorage` and attach `Authorization: Bearer <token>`.
     * **Reference & Prices:** `getDistricts()`, `getCommodities()`, `getMarkets()`, `getPriceSeries()`, `getNearbyMarkets()`.
     * **AI & Verdict:** `getForecast()`, `getModelCard()`, `getWindowRecommendation()`.
     * **Lots, Grading & Deals:** `createLot()`, `getMyLots()`, `submitSelfAssay()`, `getLotMatches()`, `getOfferThread()`, `counterOffer()`, `acceptOffer()`, `getTransactions()`.
   * Normalize ID mismatches cleanly if needed while Member 2's resolver lands.
3. **Secure Voice Integration (`api.ts` & `voiceService.ts`):**
   * Remove all direct browser/app calls to `https://api.sarvam.ai/...` and client-side `SARVAM_API_KEY` lookups from `Krishi-Mitr/src/lib/api.ts` and `voiceService.ts`.
   * Route `transcribeAudio()` $\rightarrow$ `POST ${API_BASE_URL}/voice/transcribe` (multipart upload).
   * Route `voiceService.speak()` $\rightarrow$ `POST ${API_BASE_URL}/voice/narrate`, playing returned `audio_base64` WAV, and gracefully falling back to browser `SpeechSynthesis` / `react-native-tts` if offline.
4. **Agent Client (`Krishi-Mitr/src/lib/agentApi.ts`):**
   * Implement `sendChatMessage(payload: AgentChatRequest): Promise<AgentChatResponse>` and `sendVoiceChat(audioUriOrBlob, metadata): Promise<AgentChatResponse>` with proper timeout handling (`20s`) and user-friendly Marathi/Hindi fallback messages if network drops.
5. **Voice Onboarding Upgrade (`S03_Profile.tsx` & `registrationAgent.ts`):**
   * Wire `S03_Profile` microphone flow to backend `/voice/transcribe` + optional `/agent/chat` extraction so spoken Marathi names, districts, and villages fill cleanly without relying solely on brittle client-side regex (`parseFarmerDetails.ts`).

---

## 7. Track C — Members 4 & 5: Agentic AI, Chunking, Embeddings & Vector DB

### 7.1 Member 4: Knowledge Corpus, Chunking, Embeddings, Qdrant & Evaluation
**Target Directories:** `data/rag_corpus/`, `app/rag/`, `scripts/ingest_rag.py`, `eval/`

#### Step 1: Curate the Domain Corpus (`data/rag_corpus/`)
Assemble clean Markdown / PDF documents across 4 structured folders:
1. `01_schemes_and_finance/`: WDRA e-NWR Pledge Loan guidelines, e-NAM registration & bidding rules, PMFBY crop insurance basics, Maharashtra APMC market fee/commission structure.
2. `02_grading_and_postharvest/`: AGMARK Grade A/B/C specifications for Onion, Soyabean, Tomato, Tur/Gram; NHRDF post-harvest curing, *Kanda Chawl* storage ventilation, moisture & sprouting prevention rules (aligned with `app/engines/grading_engine.py`).
3. `03_platform_mechanics/`: Detailed Krishi-Mitr documentation—how Escrow works, how FPO multi-lot pooling protects solo farmers, how the 3-round bargaining limit works, and how to read $p_{10}$ worst-case vs $p_{50}$ expected gain and `NO_ADVICE` refusal gates.
4. `04_glossary_and_mandis/`: Maharashtra APMC mandi profiles (Lasalgaon, Pimpalgaon, Nashik, Pune, Ahmednagar, Solapur, Nagpur), local varieties (*Garva*, *Pol*, *Rangda*), and colloquial weight unit definitions (*Bori*, *Goni*, *Quintal*, *Khandi*).

#### Step 2: Structure-Aware Chunking Pipeline (`app/rag/chunker.py`)
* **Two-Stage Splitter:**
  1. **Header/Section Split (`MarkdownHeaderTextSplitter`):** Preserves section hierarchy (`H1 Scheme > H2 Eligibility > H3 Documents Required`) so logical context is never mixed.
  2. **Recursive Token-Aware Split:** Target **350–450 tokens** per chunk with **60 tokens (~15%) overlap**, splitting cleanly on paragraph (`\n\n`) and Devanagari sentence boundaries (`।`, `.`, `\n`).
* **Rich Metadata Schema per Chunk:**
  ```python
  {
      "chunk_id": "wdra_pledge_04",
      "source_doc": "WDRA_Pledge_Guidelines.md",
      "section_title": "Interest Subvention & LTV Rules",
      "category": "schemes_finance",       # schemes_finance | grading | platform | glossary
      "crops": ["onion", "soyabean", "all"],
      "language": "en",                    # en | mr | hi | bilingual
      "token_count": 384
  }
  ```
* **Devanagari Text Normalization:** Run `unicodedata.normalize("NFKC", text)` before embedding/indexing to unify glyph variants (e.g., `गांव` vs `गाँव`).

#### Step 3: Embedding & Hybrid Vector Indexing (`app/rag/vector_store.py` + `scripts/ingest_rag.py`)
* **Primary Embedding Model:** `BAAI/bge-m3` (via `FlagEmbedding` / `sentence-transformers` or Hugging Face inference) **OR** `gemini-embedding-001` (if optimizing for lightweight zero-GPU deployment).
  * *Why `BAAI/bge-m3` is ideal for NLP eval:* Natively supports **Marathi, Hindi, and English** in a single vector space (cross-lingual retrieval: Marathi query retrieves English/Marathi chunks!) and generates **both Dense (1024-d) and Sparse (lexical weight) vectors**.
* **Vector DB Setup (Qdrant):**
  * Create collection `krishi_mitr_kb` with:
    * **Dense Vector Index:** Cosine similarity (`HNSW`, `m=16`, `ef_construct=100`).
    * **Sparse Vector Index (BM25 / Lexical):** Captures exact keywords (`WDRA`, `Lasalgaon`, `Grade A`, `e-NAM`, `बोरी`) that dense embeddings can blur.
    * **Payload Indexes:** Index `category`, `crops`, and `language` for sub-5ms metadata pre-filtering.
* **Retrieval Pipeline (`app/rag/retriever.py`):**
  1. Receive user query + optional `crop`/`category` filter.
  2. Run **Hybrid Search** (Dense + Sparse via **Reciprocal Rank Fusion — RRF**), returning Top-10 candidates.
  3. Apply lightweight **Reranking** (Cross-Encoder or score threshold `> 0.45`) and return **Top-4 chunks** with source citations to the Agent.

#### Step 4: Automated NLP Evaluation Suite (`eval/`)
Build reproducible scripts that produce hard numbers for the evaluation panel:
1. **`eval/rag_benchmark_dataset.json`:** 60–100 gold-standard queries across Marathi (`mr`), Hindi (`hi`), and English (`en`) paired with `expected_chunk_ids`, `expected_intent`, and `expected_tool`.
2. **`eval/eval_rag.py`:** Measures **Hit Rate@5**, **Recall@5**, **MRR (Mean Reciprocal Rank)**, and runs an **Ablation Study**:
   * Fixed 500-char chunking vs. Section-aware 400-token chunking.
   * Dense-only search vs. Hybrid (Dense + BM25 RRF) search.
   * English-only embedding vs. Multilingual (`bge-m3` / Gemini) embedding on Marathi queries.

---

### 7.2 Member 5: Agentic AI, Tool Orchestrator & Memory
**Target Directories:** `app/schemas/agent.py`, `app/agents/`, `app/engines/agent_engine.py`, `app/routers/agent.py`

1. **LLM Selection & Adapter (`app/agents/llm_client.py`):**
   * **Primary Model:** `gemini-2.5-flash` (best Marathi/Hindi fluency, native structured tool calling, low latency, low cost).
   * **Fallback / Swappable Interface:** Abstract `ILLMClient` so you can switch between Gemini, OpenAI (`gpt-4o-mini`), or Groq via `.env` without changing agent logic.
2. **Tool Registry (`app/agents/tools.py`):**
   Implement strict Pydantic-typed tools wrapping existing backend engines:
   * `tool_get_price_forecast(commodity: str, mandi: str, horizon_days: int = 14)` $\rightarrow$ wraps `price_engine.predict_range()` + `id_resolver`.
   * `tool_compute_sale_window(commodity: str, mandi: str, quantity_kg: int, grade: str = "A")` $\rightarrow$ wraps `window_engine.compute_sale_window()`. Automatically converts colloquial units if needed.
   * `tool_calculate_grade(size_uniform, colour_uniform, damage_pct, sprouting, moisture_feel, foreign_matter)` $\rightarrow$ wraps `grading_engine.grade()`.
   * `tool_create_lot_draft(commodity: str, quantity_kg: int, mandi: str, expected_price_paise: int | None)` $\rightarrow$ validates parameters and either creates a lot (if confirmed) or returns a `LOT_DRAFT` card + `PREFILL` UI action.
   * `tool_get_farmer_portfolio(user_id: int)` $\rightarrow$ fetches farmer's active lots, open offers, and escrow transaction statuses from DB.
   * `tool_search_agri_knowledge(query: str, category: str | None, crop: str | None)` $\rightarrow$ invokes Member 4's `HybridRetriever`.
   * `tool_navigate_screen(target_screen: str, params: dict)` $\rightarrow$ instructs the UI to offer one-tap navigation.
3. **Agent Execution Loop (`app/engines/agent_engine.py`):**
   * Load last 8 conversation turns from **Redis** (`DB 1`, key `agent:mem:{session_id}`, `TTL=1800s`).
   * Inject compact **System Prompt**:
     * Persona: Helpful, respectful Maharashtra Krishi-Mitr advisor.
     * Language rule: Always reply in the farmer's active locale (`mr`, `hi`, or `en`) in short, clear spoken-friendly sentences (avoid jargon like "p10 quantile"—say *"10 पैकी 1 वाईट परिस्थितीत"* / *"in the worst 1-in-10 case"*).
     * Grounding rule: Never invent prices, percentages, or loan rates; always cite tool outputs or RAG chunks.
     * Screen context injection: Append `[User is currently viewing: {current_screen}, Commodity: {active_commodity_id}]`.
   * Run **Tool-Calling Loop (Max 3 iterations)** $\rightarrow$ execute requested tools in parallel if multiple $\rightarrow$ synthesize final `AgentChatResponse` with `cards`, `ui_action`, `quick_replies`, and `citations`.
   * Log turn metadata (`intent_detected`, `tools_called`, `latency_ms`) asynchronously to `VoiceInteraction` / DB.
4. **FastAPI Router (`app/routers/agent.py`):**
   * Mount at `/api/v1/agent` in `app/main.py`.
   * Expose:
     * `POST /api/v1/agent/chat` (Text chat; optional JWT—gracefully degrades to guest/onboarding mode before login, authenticated mode for `create_lot`/`my_lots`).
     * `POST /api/v1/agent/voice-chat` (Audio upload $\rightarrow$ `IVoiceProvider.speech_to_text` $\rightarrow$ `AgentEngine.run` $\rightarrow$ optional `IVoiceProvider.text_to_speech`).
     * `DELETE /api/v1/agent/session/{session_id}` (Clear conversation memory).
5. **Agent Evaluation (`eval/eval_agent.py`):**
   * Evaluate **Intent Detection Macro-F1**, **Slot Extraction F1** (quantity kg normalization accuracy, commodity & mandi canonicalization), **Tool Selection Accuracy**, and **Groundedness / Hallucination Rate** across 50 end-to-end test prompts.

---

## 8. Phased Execution Timeline & Parallel Milestones

Assume a focused **7-Day Sprint** (compressible to 3–4 days for hackathon pace):

| Phase | Member 1 (UI/Chat) | Member 2 (Backend/Cache) | Member 3 (KM Integration) | Member 4 (RAG/Eval) | Member 5 (Agent/Tools) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Day 1: Setup & Contracts** | Audit Farmer screens (`S01`–`S38`), fix layout/Marathi text bugs; scaffold `AgentContext`. | Add `qdrant` to Docker; build `id_resolver.py`; fix `prices.py` `/nearby`. | Set up `httpClient.ts` & `API_BASE_URL` switch; proxy Voice endpoints. | Collect & clean 4-bucket corpus (`data/rag_corpus/`); design chunk schema. | Build `schemas/agent.py`, `llm_client.py`, and Redis session memory. |
| **Day 2–3: Core Build (Isolated)** | Build `FloatingAssistant`, `ChatDrawer`, `ChatCards` using mock JSON from Contract 1. | Add `@cache` to `ref.py`/`prices.py`; extend DB logging; verify Farmer `lots` & `auth` APIs. | Wire `auth`, `ref`, `prices`, `ai` (`forecast`/`window`), `lots` & `grading` screens to real FastAPI. | Implement `chunker.py`, `bge-m3`/Gemini embeddings, Qdrant hybrid indexing (`ingest_rag.py`). | Wrap `price_engine`, `window_engine`, `grading_engine`, `lot_service` as Agent Tools; build `/agent/chat`. |
| **Day 4: First Integration** | Connect `ChatDrawer` to Member 3's `agentApi.ts` + live voice mic & playback. | Run `benchmark_redis.py` (with vs. without cache); verify CORS & auth edge cases. | End-to-end smoke test of complete Farmer flow (`S01` $\rightarrow$ `S04` $\rightarrow$ `S09` $\rightarrow$ `S15` $\rightarrow$ `S27`). | Connect `HybridRetriever` into Member 5's `tool_search_agri_knowledge`. | Implement `POST /agent/voice-chat` (STT + Agent + TTS) & `ui_action` deep-link payloads. |
| **Day 5: Deep Polish & Eval** | Upgrade `S28_Assistant`; test deep-link navigation (`Agent` $\rightarrow$ `S9_Verdict` / `S15_MyLots`). | Load test DB + Redis + Qdrant container orchestration (`docker-compose up`). | Offline fallback testing (`USE_FIXTURES` resilience on network timeout). | Run `eval_rag.py`: compute **Recall@5**, **MRR**, and **Chunk/Hybrid Ablations**. | Run `eval_agent.py`: compute **Intent F1**, **Slot F1**, **Tool Accuracy**, and **Zero-Hallucination check**. |
| **Day 6–7: E2E & Demo Prep** | Cross-browser & Android device UI/voice walkthroughs; zero-glitch polish. | Finalize API docs, health checks, and benchmark charts. | Full integration regression test across Farmer web & mobile builds. | Freeze RAG evaluation report, confusion matrices, and Qdrant dashboard demo. | Record end-to-end Marathi voice agent demo & verify refusal gates (`NO_ADVICE`). |

---

## 9. Integration, Testing & Verification Checklist

Run these checks before declaring integration complete:

### Backend & Integration Checks
- [ ] `docker-compose up` brings up `postgis`, `pgbouncer`, `redis`, `qdrant`, `minio`, `api`, and `celery` cleanly.
- [ ] `pytest tests/` passes all existing 140+ unit/integration tests plus new tests in `tests/test_agent.py` and `tests/test_rag.py`.
- [ ] `GET /api/v1/ref/markets` and `GET /api/v1/prices/nearby?commodity_id=cmd_onion&district_id=dist_nashik` work with both slug strings and integer IDs and show Redis cache hit speedup (`scripts/benchmark_redis.py`).
- [ ] `POST /api/v1/voice/transcribe` and `POST /api/v1/voice/narrate` work with zero Sarvam keys present in `Krishi-Mitr/`.

### Agentic AI & RAG Checks
- [ ] **Onboarding via Agent:** Farmer speaks/types *"माझं नाव रमेश पाटील, गाव निफाड, जिल्हा नाशिक"* $\rightarrow$ slots extracted accurately.
- [ ] **Colloquial Unit Normalization:** *"माझ्याकडे २० बोरी कांदा आहे"* $\rightarrow$ `tool_compute_sale_window` receives `quantity_kg=1000` (not `20`).
- [ ] **Refusal Gate Enforcement:** High-volatility test query returns `NO_ADVICE` with transparent explanation instead of fabricated advice.
- [ ] **RAG Grounding:** Query *"गोदामात कांदा ठेवून कर्ज कसे मिळते?"* invokes `search_agri_knowledge`, retrieves WDRA chunk, and includes `citations`.
- [ ] **Latency Budget:** Text `/agent/chat` responds in **< 2.0s**; `/agent/voice-chat` responds in **< 3.5s**.

### Frontend UI Checks
- [ ] `npm run typecheck` and `npm run build` in `Krishi-Mitr/` succeed with zero TypeScript errors.
- [ ] Floating assistant button appears consistently across Farmer tabs without overlapping tab icons or primary buttons.
- [ ] Tapping `ui_action` CTA inside chat successfully navigates to `S9_Verdict` or pre-fills `S15_MyLots` / `S19_Quantity`.

---

## 10. NLP Evaluator Defense & Benchmark Playbook

When presenting to an **NLP Evaluation Panel**, structure your defense around **empirical metrics and NLP engineering depth**, not just the LLM API:

### 1. What Evaluators Will Ask & How You Answer

| Evaluator Question | Winning Technical Answer |
| :--- | :--- |
| **"Did you just wrap an LLM API?"** | *"No. We engineered an **Agentic Hybrid RAG + Deterministic Tool-Calling pipeline** specifically adapted for rural Marathi/Hindi. We built a custom Devanagari Unicode normalizer (NFKC), agrarian unit canonicalizer (`bori` $\rightarrow$ `kg`), section-aware recursive chunker, multilingual dense+sparse (`BGE-M3` + BM25) Qdrant index, and Redis session memory—and we evaluated every stage quantitatively."* |
| **"Why use a Vector DB if you have an LLM?"** | *"LLMs hallucinate state-specific schemes like WDRA LTV ratios or APMC commission rules, and putting all manuals in the system prompt destroys latency and token budgets. Our Vector DB grounds answers in verified agricultural documents with explicit source citations, while PostgreSQL/LightGBM tools handle all live pricing math."* |
| **"How did you choose your chunk size and embedding model?"** | *"We ran an empirical ablation study (`eval/eval_rag.py`) comparing 256 vs. 400 vs. 800 token chunks and Dense-only vs. Hybrid (Dense + Sparse RRF) retrieval on 80 Marathi/Hindi/English queries. Section-aware 400-token chunks with 15% overlap and Hybrid RRF improved Recall@5 from X% to Y% because sparse vectors preserved exact Marathi crop and mandi names."* |
| **"How do you prevent dangerous hallucinations for farmers?"** | *"Two layers: (1) Price and hold/sell decisions never come from the LLM—they are computed by our LightGBM quantile regression and deterministic refusal gate (`window_engine.py`, MASE 0.5718). (2) Domain policy answers are strictly grounded in retrieved Qdrant chunks with low LLM temperature (`0.1–0.2`) and verified against a faithfulness rubric."* |

### 2. Metrics Table to Include in Your Final Report / Slides

| Pipeline Component | Metrics to Report (Measured via `eval/`) | Target Threshold |
| :--- | :--- | :--- |
| **RAG Retrieval** | Hit Rate@5, Recall@5, Mean Reciprocal Rank (MRR) | Recall@5 > 88%, MRR > 0.78 |
| **Chunking / Hybrid Ablation** | Dense-Only vs. Hybrid (Dense + BM25 RRF) Delta | Measurable +8–15% gain on vernacular terms |
| **Intent & Tool Selection** | Macro F1-Score across core intents (`PRICE`, `WINDOW`, `LOT`, `RAG`, `ONBOARD`) | Macro F1 > 92% |
| **Entity / Slot Extraction** | Slot F1 (`commodity`, `mandi`, `quantity_kg`, `grade`) | Slot F1 > 88% |
| **Safety / Faithfulness** | Refusal Gate compliance on high-uncertainty queries; Zero fabricated price errors | 100% refusal compliance |
| **System Performance** | Redis Cache Latency Reduction (`scripts/benchmark_redis.py`) & E2E Agent Latency | P95 < 2.0s (text), Redis hit < 5ms |
