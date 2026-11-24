# Track B — Backend & Integration Plan (Members 2 & 3)

> **Scope:** Only Track B from `NLP_Execution_Plan.md`.
> **Not ours:** the agent and RAG (Track C: Members 4 & 5) and the UI/chat widget (Track A: Member 1).
> **Our job:** make the farmer API correct and live, connect Krishi-Mitr to it, and build the **seams** the agent team plugs into, so nobody waits on anybody else.

---

## 0. What the code shows today (checked against the repo)

| # | Finding | Where | Impact |
|---|---|---|---|
| 1 | `lot_service` does `int(payload.commodity_id)` but the app sends `"cmd_onion"` | `app/services/lot_service.py:41-43` | **`POST /lots` returns 500 from the app.** Blocker. |
| 2 | Ref tables (`districts`, `commodities`, `mandi_locations`, `warehouses`) have **no slug column** | `app/models/reference.py`, `app/models/mandi.py` | We can't resolve `cmd_onion` to an ID without one |
| 3 | `/prices/series` and `/prices/nearby` take `int` IDs; `/nearby` is fully mocked (`gross=250000`, `distance_km=45`) | `app/routers/prices.py:13-100` | The market screen shows fake numbers |
| 4 | Redis cache is only used on `mandi.py`, which **isn't mounted** | `app/main.py`, `app/routers/mandi.py` | No caching anywhere in practice |
| 5 | `VoiceInteraction.user_id` is `nullable=False` | `app/models/voice.py` | Guest/onboarding agent turns **can't be logged** |
| 6 | Only `get_current_user` exists, with no optional-auth variant | `app/dependencies/auth.py` | The agent's guest mode has no dependency to use |
| 7 | Redis cache uses DB 1, and the NLP plan puts agent memory on DB 1 too | `docker-compose.yml`, NLP plan §7.2 | **Key collision.** Move agent memory to DB 2 |
| 8 | No Qdrant container, no LLM/Qdrant settings | `docker-compose.yml`, `app/config.py`, `.env.example` | The agent team can't run anything end to end |
| 9 | `USE_FIXTURES = true`; `PROD_HOST` is a placeholder | `Krishi-Mitr/src/config.ts:54,112` | The app never touches the backend |
| 10 | Web build uses same-origin `/api/v1`; `vercel.json` only rewrites to `index.html`; voice goes to Vercel functions in `Krishi-Mitr/api/v1/voice/*` | `Krishi-Mitr/vercel.json`, `config.ts` | **The web build cannot reach FastAPI at all** |
| 11 | The client calls `api.sarvam.ai` directly and reads `SARVAM_API_KEY` from `window`/`localStorage`/env | `Krishi-Mitr/src/lib/api.ts:~420-520`, `Krishi-Mitr/src/lib/voiceService.ts:~20-60` | Key-exposure risk; violates "no keys in the app" |
| 12 | Known contract gaps: no `GET /transactions` (list mine); accepted `OfferDto` has no `tx_id`; no `GET /buyers/{id}` (only `/reliability`) | `app/routers/transactions.py`, `offers.py`, `buyers.py` | The deals screens fall back to empty states |

Everything below fixes these, in priority order.

---

## 1. Ownership split

| | **B1: Backend** (Member 2) | **B2: Integration** (Member 3) |
|---|---|---|
| Owns | `app/routers/{ref,prices,lots,ai,transactions,offers}.py`, `app/services/*`, `app/models/*`, `app/utils/*`, `app/dependencies/*`, `alembic/`, `docker-compose.yml`, `requirements.txt`, `app/config.py`, `.env.example`, `nginx.conf` | `Krishi-Mitr/src/config.ts`, `Krishi-Mitr/src/lib/{httpClient,api,agentApi,voiceService,auth}.ts(x)`, `Krishi-Mitr/src/types/agent.ts`, `Krishi-Mitr/vercel.json`, `Krishi-Mitr/api/*`, `scripts/smoke_*.py` |
| Doesn't touch | `app/agents/*`, `app/rag/*`, `app/engines/agent_engine.py`, `app/routers/agent.py` (Track C) | `src/components/chat/*`, `src/screens/*` layout, `AgentContext` (Track A) |

**Rule:** if B2 needs a backend change, they file it as a line in §6 ("Contract change log") and B1 makes it. Neither of us edits Track C files. We expose helpers *they* import.

---

## 2. Phase 0: Kickoff with the agent and UI teams (60 min, Day 1 morning)

We run this meeting because we own the contracts. Leave with these frozen:

1. **`AgentChatRequest` / `AgentChatResponse`** exactly as in NLP plan §4 Contract 1. Add two fields now so nobody has to change the contract later:
   - `response.error_code: str | null` (e.g. `LLM_UNAVAILABLE`, `NO_ADVICE`) so the UI can render a fallback without parsing text.
   - `response.turn_id: str` for log correlation and later feedback.
   - Freeze the enum values: `intent_detected ∈ {PRICE, SALE_WINDOW, GRADE, LOT_CREATE, PORTFOLIO, KNOWLEDGE, ONBOARD, SMALLTALK, UNKNOWN}`, `cards[].type ∈ {WINDOW_VERDICT, PRICE_SNAPSHOT, LOT_DRAFT, RAG_CITATION, ONBOARD_PROFILE}`, `ui_action.type ∈ {OFFER_NAVIGATION, PREFILL}`, plus the **list of legal `target_screen` names** (pull them from `navigation/*.tsx`).
2. **What we hand Track C** (the helper signatures they'll import):
   ```python
   # app/utils/id_resolver.py
   async def resolve_commodity(db, ref: str | int) -> int      # raises NotFoundError
   async def resolve_market(db, ref: str | int) -> int
   async def resolve_district(db, ref: str | int) -> int
   async def commodity_slug(db, id: int) -> str                # reverse, for cards
   # app/dependencies/auth.py
   async def get_optional_user(...) -> User | None
   # app/services/agent_log_service.py
   async def log_agent_turn(db, *, session_id, user_id, screen_context, transcript,
                            intent, tools_called, rag_sources, latency_ms, error_code) -> None
   # app/config.py → settings.LLM_PROVIDER, GEMINI_API_KEY, QDRANT_URL, QDRANT_COLLECTION,
   #                  EMBEDDING_MODEL, AGENT_MEMORY_REDIS_URL (redis://redis:6379/2)
   ```
3. **What we need from Track C by end of Day 1:** their extra pip dependencies (for `requirements.txt` and the Docker image), and the embedding model choice. If it's **BGE-M3 (~2.2 GB, ~2-3 GB RAM)** that decides the EC2 instance size and the image build time, so we need to know now.
4. **Agent stub:** we ship a stub `/api/v1/agent/chat` (§3, B1-7) on Day 1 that returns contract-valid canned responses. Member 1 builds against it and Track C replaces it. Nobody is blocked.

---

## 3. B1: Backend work items (in order)

### P0: Blockers (Day 1)

**B1-1. Slug columns + ID resolver**
- Alembic migration `004_ref_slugs`: add `slug VARCHAR(64) UNIQUE` to `districts`, `commodities`, `mandi_locations`, `warehouses`. Backfill via `scripts/seed_data.py` using the canonical strings the app already uses (`cmd_onion`, `mkt_lasalgaon`, `dist_nashik`, … taken from `Krishi-Mitr/src/fixtures/reference.ts` so they match exactly).
- `app/utils/id_resolver.py`: accept `"12"`, `12`, or `"cmd_onion"`. Cache the slug→id map in process (the ref tables are tiny and static) and reload it on seed. On a miss, raise a 404 using the standard error envelope with `field` set.
- Apply it in: `lot_service.create_lot` (replace the `int()` calls), `prices.py` (`/series`, `/nearby`), `ai.py` (`/forecast`, `/window/recommend`), and the `/ref/markets?district_id=` filter.
- Ref responses return **both** `id` and `slug_id`, so the app can migrate gradually.
- Tests: `tests/test_id_resolver.py` covers slug, int, numeric string, unknown → 404, plus `POST /lots` with `commodity_id="cmd_onion"` → 201.

**B1-2. Optional auth dependency.** Add `get_optional_user` to `app/dependencies/auth.py`: it returns `None` when there's no header, and **401 when a token is present but invalid** (don't silently downgrade a bad token to guest).

**B1-3. Infra for Track C**
- `docker-compose.yml`: add `qdrant` (`qdrant/qdrant:v1.12.x` pinned, not `latest`; ports 6333/6334; volume `qdrantdata`). `api` gets `depends_on: qdrant`.
- Redis DB map, written down in `.env.example`: **0 = Celery, 1 = HTTP cache, 2 = agent memory.**
- `app/config.py` + `.env.example`: the settings from §2.2, all optional with safe defaults, so the API still boots with no LLM key.
- `requirements.txt` / `Dockerfile`: add Track C's dependencies. If they pick BGE-M3, download the model **at image build time**, not first request, or the first demo query takes ~60 s.

**B1-4. Agent turn log table**
- Migration `005_agent_turns`: `agent_turns(id, turn_id, session_id, user_id NULL FK, locale, screen_context JSONB, transcript, reply_text, intent_detected, tools_called JSONB, rag_sources JSONB, latency_ms INT, error_code, created_at)`. Index `(session_id, created_at)`.
- `app/services/agent_log_service.py::log_agent_turn()`: fire-and-forget (`asyncio.create_task` with its own session), so **a logging failure never fails a chat turn**.
- Leave `VoiceInteraction` alone, so existing voice tests don't break.

### P1: Make the farmer API real (Day 2)

**B1-5. Real `/prices/nearby`**
- Inputs: `commodity_id`, `district_id` (both via the resolver), optional `lat`/`lng`, `radius_km` (default 150), `qty_kg` (default 1000).
- Origin point: `lat/lng` query params → the JWT user's `lat/lng` → the centroid of the district's mandis.
- Query: latest `PriceObservation` per market for the commodity within the last 14 days (`DISTINCT ON (market_id) … ORDER BY market_id, date DESC`), joined to `MandiLocation`, filtered with `ST_DWithin` on `geom` (there's already a GIST index).
- Costs: `LogisticsCostRoute(from_district_id, to_market_id)` if a row exists, else `haversine_km × per-km rate` from `app/domain/costs.py`. Commission from `COMMISSION_RATE_BPS`. Reuse `compute_costs()` rather than re-deriving it.
- `distance_km` is the real distance. `source` = the observation's `observation_type`, and the transport source becomes `IMPUTED` when it fell back to haversine.
- Empty result → `rows: []` with `as_of_date`, not a 500.
- Test: a seeded district returns rows sorted by `net_paise_per_qtl` descending, with every field an integer.

**B1-6. Close the contract gaps from finding #12**
- `GET /transactions` returns the caller's transactions, with the user taken from the JWT (security rule §5.1).
- Add `tx_id` to `OfferDto` when status is `ACCEPTED`.
- `GET /buyers/{id}`: public buyer profile (name, company, `verified`, reliability). Return 404 for non-buyers.

**B1-7. Agent stub router** (Day 1 afternoon, ~1 hr)
- `app/routers/agent_stub.py`, mounted at `/api/v1/agent` **only when** `settings.AGENT_STUB=true`.
- Keyword switch on the message: "कधी/when" → the `WINDOW_VERDICT` example, "भाव/price" → `PRICE_SNAPSHOT`, "लॉट/lot" → `LOT_DRAFT`, anything else → plain text with a citation chip. It validates against Track C's `app/schemas/agent.py` the moment that file exists.
- Once Track C mounts the real `/agent` router, set the flag to false. Nothing else changes.

**B1-8. Redis caching**
- `@cache(expire=3600)` on `ref.py` (`/districts`, `/commodities`, `/markets`, `/warehouses`).
- `@cache(expire=300)` on `/prices/series`, `/prices/nearby`, `/ai/forecast`.
- **Don't cache** `POST /ai/window/recommend` (fastapi-cache only caches GET) or anything user-scoped (`/lots`, `/transactions`, `/auth/me`).
- `scripts/reset_db.py` / `seed_data.py` must `FLUSHDB` Redis DB 1, or stale cached ref data will hide your seed changes.
- Delete or mount `app/routers/mandi.py`. Recommendation: delete it, since `/ref/markets` replaces it.
- `scripts/benchmark_redis.py`: P50/P99 and RPS with the cache bypassed vs. enabled (this goes on the evaluator slide).

### P2: Hardening (Day 3)

**B1-9. Rate limit the paid, unauthenticated endpoints.** `/voice/*` and `/agent/*` are open (by design, for onboarding) and each call costs Sarvam or LLM money. Add a Redis fixed-window limiter per IP (e.g. 20/min, 300/day), returning a 429 envelope with `RATE_LIMITED`. That's about 30 lines of middleware or a dependency.

**B1-10. Timeouts and health**
- nginx: keep `proxy_read_timeout 120s`, but **turn off `proxy_next_upstream` retries for `/api/v1/agent` and `/voice`**. Retrying a slow LLM call doubles the cost and the latency.
- Extend `/api/v1/meta/health` to report `db`, `redis`, `qdrant`, `models_loaded`, `voice_configured`, `llm_configured`. Use it in the deploy check and the demo-day pre-flight.

**B1-11. CORS.** Replace `allow_origins=["*"]` + `allow_credentials=True` (browsers reject that combination anyway) with the Vercel domain + `localhost:8080`.

**B1-12. Tests that must pass:** the existing 14 test files, plus `test_id_resolver.py`, `test_prices_nearby.py`, `test_agent_contract.py` (stub, and later the real router, validate against the schema), and `test_rate_limit.py`.

---

## 4. B2: Integration work items (in order)

### P0: Unblock the live connection (Day 1)

**B2-1. Decide and wire the web → API path.** The web build calls same-origin `/api/v1`, and nothing forwards it to FastAPI today.
- **Recommended:** add a Vercel rewrite **above** the SPA catch-all:
  ```json
  { "source": "/api/v1/:path*", "destination": "https://<api-host>/api/v1/:path*" }
  ```
  This keeps `API_BASE_URL = '/api/v1'`, needs no CORS, and keeps keys off the client.
- Give the EC2 host a domain + TLS (Caddy or certbot on nginx). The phone build also needs HTTPS, or Android cleartext exceptions.
- Then **delete `Krishi-Mitr/api/v1/voice/*`** (the Vercel serverless voice functions). Otherwise there are two voice backends with two copies of the Sarvam key, and the rewrite order decides which one you get. Tell Kartik/Pranay before deleting, because the live landing page may depend on them.
- Fill in the real host for `PROD_HOST` in `config.ts`.

**B2-2. `httpClient.ts`** (new; every call goes through it)
- Base URL from `config.ts`. Attaches `Authorization: Bearer` when a token exists.
- `AbortController` timeout: 10 s default, 20 s for `/agent/chat`, 30 s for `/agent/voice-chat`.
- Parses the `{error:{code,message,field}}` envelope into a typed `ApiError`. On `401` it clears the token and routes to `S02_Phone`.
- On a network error or timeout for **read** endpoints with a fixture available, it returns the fixture with `stale: true`, so screens show `StaleBanner` honestly. Writes (`POST`/`PATCH`) never fall back silently.

**B2-3. Generate types from the backend instead of guessing**
- Run `scripts/export_openapi.py`, then `npx openapi-typescript openapi.json -o src/types/api.gen.ts`.
- Diff against the hand-written `src/types/api.ts`. Every mismatch becomes a line in §6 for B1, or a fix in the app. This replaces "click around and hope".

### P1: Wire every farmer endpoint (Days 1-2)

**B2-4. Flip `USE_FIXTURES` to `false` and wire `api.ts` group by group**, smoke-testing each group on a device before moving on:

| Order | Group | Functions | Backend route | Watch for |
|---|---|---|---|---|
| 1 | Auth | `requestOtp`, `verifyOtp`, `registerFarmer`, `getMe`, `updateLocale` | `/auth/*` | JWT in AsyncStorage; `/auth/locale` must also update the agent's default locale |
| 2 | Reference | `getDistricts`, `getCommodities`, `getMarkets` | `/ref/*` | Use `slug_id` once B1-1 lands |
| 3 | Prices | `getPriceSeries`, `getNearbyMarkets` | `/prices/*` | `/nearby` is fake until B1-5 lands |
| 4 | AI | `getForecast`, `getModelCard`, `getWindowRecommendation` | `/ai/*` | `NO_ADVICE` must render the refusal screen, not an error |
| 5 | Lots | `createLot`, `getMyLots`, `submitSelfAssay`, `getPriceSuggestion`, `getLotMatches` | `/lots/*` | Blocked on B1-1. Replace `DEFAULT_LOT_ID` / `DEFAULT_QTY_KG` with the real lot |
| 6 | Deals | `getOfferThread`, `counterOffer`, `acceptOffer`, `getTransactions` | `/offers/*`, `/transactions` | Blocked on B1-6 for the list and `tx_id` |

Check after the flip: `FIXTURE_LOTS_EMPTY = false`, and `npm run typecheck` passes.

**B2-5. Move voice onto the backend**
- `api.ts` `transcribeAudio()`: delete the direct `api.sarvam.ai` call and the key lookup. Always `POST ${API_BASE_URL}/voice/transcribe` (multipart, field `audio`, plus `locale`).
- `api.ts` / `voiceService.ts` TTS: delete the direct call and **all** `SARVAM_API_KEY` reads (window, localStorage, `process.env`). Use `POST /voice/narrate`, play the base64 WAV, and fall back to Web Speech / `react-native-tts` on failure.
- Then `grep -ri sarvam Krishi-Mitr/src` should only show comments. Add that grep to CI (`.github/workflows/deploy.yml`) so a key can't come back.

### P1: Agent client for Member 1 (Day 2)

**B2-6. `src/types/agent.ts` + `src/lib/agentApi.ts`**
- Types are a one-to-one mirror of the frozen contract (§2.1).
- `sendChatMessage(req)` → `POST /agent/chat`.
- `sendVoiceChat(audio, meta)` → `POST /agent/voice-chat` multipart. **Gotcha:** React Native needs `{uri, name:'clip.m4a', type:'audio/m4a'}`, while web needs a `Blob`. Handle both in one helper, and send `screen_context` as a JSON string field.
- `session_id`: generate once per app session (`sess_<userId|guest>_<random>`), keep it in memory, and expose `resetSession()` → `DELETE /agent/session/{id}`.
- Failure behaviour: if the call times out or fails, return a **contract-shaped** response with `error_code` set and a localized `reply_text` ("नेटवर्क कमकुवत आहे, पुन्हा प्रयत्न करा"). Member 1's UI then has a single code path.
- `MOCK_AGENT=true` flag returns canned responses locally, so Member 1 can work offline before the B1-7 stub is deployed.
- **Hand-off to Member 1:** these two files plus the list of `target_screen` → route-name mappings. Member 1 owns `AgentContext`, the drawer, the cards and the navigation.

**B2-7. Onboarding voice (S03_Profile).** Point the mic at `/voice/transcribe` (done by B2-5). Once Track C ships `ONBOARD` intent extraction, send the transcript to `/agent/chat` with `current_screen: "S03_Profile"` and fill the form from the `ONBOARD_PROFILE` card (`{name, village, district_id}`). Keep `parseFarmerDetails.ts` as the offline fallback. **Do this one last.** It depends on Track C and isn't on the demo critical path.

### P2: Verify (Days 3-4)

**B2-8. API smoke script.** Extend `scripts/test_all_apis.py` into `scripts/smoke_farmer_flow.py`, which runs the whole flow and exits non-zero on the first failure:
`otp → verify → me → ref → prices/series → prices/nearby → ai/forecast → window/recommend → POST lot (slug IDs) → assay → price-suggestion → matches → offer accept → transactions → agent/chat (3 canned prompts) → voice/narrate`.
Run it against local, then staging, then prod. It's also the demo-morning pre-flight.

**B2-9. Device and network passes**
- Android over `adb-reverse`, Android over LAN, and the web build on Vercel against the deployed API.
- Chrome DevTools "Slow 3G": the agent replies within the timeout, otherwise the localized fallback shows. Nothing hangs.
- Airplane mode: read screens show fixtures + `StaleBanner`, writes show a clear error, the agent shows the offline message.

**B2-10. Demo fallback ladder.** Rehearse it once, end to end:
1. Deployed API.
2. Laptop API over a phone hotspot.
3. `USE_FIXTURES=true` rebuild.

Write down the exact commands for each step in the README.

---

## 5. Timeline (4 working days, two people in parallel)

| Day | B1: Backend | B2: Integration | Sync point (end of day) |
|---|---|---|---|
| **1** | Kickoff · B1-1 resolver + slugs · B1-2 optional auth · B1-3 Qdrant/env/Redis DBs · B1-7 agent stub | Kickoff · B2-1 Vercel rewrite + TLS · B2-2 httpClient · B2-3 type diff · B2-4 groups 1-2 | `POST /lots` with `cmd_onion` works from the app. Stub `/agent/chat` reachable from the web build. Track C has its env vars and Qdrant. |
| **2** | B1-4 agent_turns · B1-5 real `/nearby` · B1-6 contract gaps · B1-8 caching | B2-4 groups 3-6 · B2-5 voice to backend · B2-6 agentApi handed to Member 1 | Full farmer flow runs on live API. Zero Sarvam keys in the app. Member 1 is rendering cards from the stub. |
| **3** | B1-9 rate limit · B1-10 health/timeouts · B1-11 CORS · B1-12 tests · benchmark | B2-8 smoke script · swap the stub for the real agent when Track C is ready · B2-7 onboarding voice (if Track C is ready) | Real agent behind `/agent/chat`. `smoke_farmer_flow.py` green on staging. |
| **4** | Deploy to EC2, pre-flight `/meta/health`, help Track C with latency | B2-9 device/network passes · B2-10 fallback ladder rehearsal | Green on prod. Rehearsal done. |

**Critical path:** B1-1 (resolver) → B2-4 group 5 (lots) → agent `LOT_DRAFT` → create lot. If B1-1 slips, everything lot-related slips, including the agent's best demo moment, so **B1-1 is the first thing written on Day 1.**

---

## 6. Contract change log

Append-only. Any change to a request or response shape goes here *before* the code, with a date and owner, and gets posted in the team chat.

| Date | Endpoint | Change | Requested by | Done |
|---|---|---|---|---|
| D1 | `/ref/*` | add `slug_id` | B2 | |
| D1 | `AgentChatResponse` | add `error_code`, `turn_id` | B1/B2 | |
| D2 | `GET /transactions` | new list endpoint (JWT-scoped) | B2 | |
| D2 | `OfferDto` | add `tx_id` when ACCEPTED | B2 | |
| D2 | `GET /buyers/{id}` | new | B2 | |
| D2 | `/prices/nearby` | accept slug IDs, `lat/lng/radius_km/qty_kg` | B2 | |

---

## 7. Definition of done (Track B)

- [ ] `docker-compose up` brings up postgis, pgbouncer, redis, **qdrant**, minio, api, celery_worker, nginx; `/meta/health` is all green.
- [ ] `pytest` passes: the existing tests plus resolver, nearby, agent-contract and rate-limit tests.
- [ ] Every farmer endpoint accepts **both** slug and integer IDs.
- [ ] `/prices/nearby` returns real, distance-sorted, integer-paise rows; no constants remain in `prices.py`.
- [ ] Cached GETs show a measurable speed-up in `benchmark_redis.py`; user-scoped routes are not cached.
- [ ] `/voice/*` and `/agent/*` are rate-limited; nginx doesn't retry them.
- [ ] `grep -ri "sarvam.ai\|SARVAM_API_KEY" Krishi-Mitr/src` returns nothing executable; the CI guard is in place.
- [ ] `USE_FIXTURES=false`, `FIXTURE_LOTS_EMPTY=false`; `npm run typecheck` and `npm run build` are clean.
- [ ] The web build on Vercel and the Android build both run the full flow against the deployed API.
- [ ] `agentApi.ts` is handed to Member 1; agent turns appear in `agent_turns` for both guest and logged-in users.
- [ ] `smoke_farmer_flow.py` is green on prod the morning of the demo.

---

## 8. Risks we own

| Risk | Mitigation |
|---|---|
| BGE-M3 doesn't fit in EC2 RAM next to Postgres + LightGBM | Get the decision on Day 1 (§2.3). Either size up the instance, or Track C uses `gemini-embedding-001` for query-time embeddings |
| Vercel → EC2 rewrite adds latency, or times out on slow agent turns | Measure on Day 1 with the stub. If it's bad, the web build calls the API host directly and we enable CORS for that origin |
| Slug backfill doesn't match the app's fixture IDs | Generate the slug seed **from** `Krishi-Mitr/src/fixtures/reference.ts`, not by hand |
| Track C slips | The stub stays mounted. The demo still shows the chat UI with deterministic cards, and the core farmer flow doesn't depend on the agent |
| A leaked LLM key gets abused through the open `/agent` endpoint | Rate limiting (B1-9), plus a spend cap set in the provider console |
