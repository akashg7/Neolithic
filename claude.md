# AgriSense — Final Backend Architecture, AI Pipelines & Team Alignment
### PS 26132 | 2 Days Remaining | Single source of truth for all 6 teammates

---

## 0. Status Confirmation (per your last message)

- **Clause 1 (mandi prices, arrival volumes):** ✅ Real live/historical Agmarknet data. Confirmed, no changes.
- **Clause 3 (buyer KYC verification):** Stays as a **simple verification flag/badge** in the prototype (a boolean `verified` field an admin can toggle) — real Aadhaar/GST-linked KYC is correctly out of scope for 2 days. This was already tagged 🔵 Phase 2 in the checklist; no change needed, just confirming you're not expected to build real KYC now.
- **Clause 4 additions (WebRTC negotiation calling, AI-assisted negotiation, voice AI, local language):** **New, Tier 3 (stretch-only)** — architecture included below so it's ready to build if time allows, but it does not replace anything already committed.

---

## 1. Complete Backend Architecture (updated)

```
┌───────────────────────────────────────────────────────────────────┐
│              React Native App (Expo) — role-based                  │
│   Farmer Stack │ Buyer Stack │ FPO screens │ [Stretch: Call screen] │
└───────────────────────────────┬───────────────────────────────────┘
                                 │ REST (JWT) + WebSocket (calls, stretch)
┌─────────────────────────────────▼─────────────────────────────────┐
│                    FastAPI Backend — Modular Engines                │
│                                                                       │
│  Auth Engine        │ Lot Engine         │ Matching Engine (multi-lot)│
│  Offer Engine       │ Payment Engine      │ Dispute Engine            │
│  FPO Aggregation    │ Price Engine (TFT/LGBM) │ Window+Refusal Engine │
│  Grading Engine (self-assay)                                         │
│  ── Tier 3 (stretch) ──                                              │
│  Voice/Language Engine (STT/TTS/translation)                        │
│  Call Signaling Engine (WebRTC session management)                  │
└──────┬───────────────┬────────────────┬─────────────────┬───────────┘
       │               │                │                 │
  ┌────▼────┐   ┌──────▼──────┐  ┌──────▼──────┐   ┌──────▼─────────┐
  │ Postgres│   │ S3 (photos, │  │  Razorpay    │   │ Bhashini/Sarvam │
  │ (Docker)│   │ call logs)  │  │  Test Mode   │   │ API (Tier 3)    │
  └─────────┘   └─────────────┘  └──────────────┘   └─────────────────┘
                                                       ┌─────────────────┐
                                                       │ Agora/ZegoCloud │
                                                       │ (WebRTC, Tier 3)│
                                                       └─────────────────┘

  All core services (Tier 1/2) on a single AWS EC2 instance via docker-compose.
  Tier 3 services (Bhashini, Agora) are external managed APIs — no extra
  infra to host, just API keys and SDK integration.
```

---

## 2. Complete Database Schema (final — includes prior fixes)

**Money and quantity fields use integers with units in the name — no floats for currency, per the earlier review.**

```sql
users(id, name, phone, role[farmer|buyer|fpo_admin], lat, lng,
      preferred_language, verified, created_at)

fpos(id, name, region)
farmers(user_id FK, fpo_id FK nullable)
buyers(user_id FK, company_name, verified_status)

mandi_locations(id, name, district, lat, lng)          -- seeded, no geocoding API

buyer_demand(id, buyer_id FK, crop, desired_qty_kg, desired_grade,
             max_price_paise_per_qtl, lat, lng)

lots(id, farmer_id FK, fpo_id FK nullable, crop, quantity_kg, grade,
     image_url, self_assay_answers JSON, lat, lng,
     price_min_paise_per_qtl, price_mid_paise_per_qtl, price_max_paise_per_qtl,
     status, created_at)

offers(id, buyer_id FK, offered_price_paise_per_qtl, total_quantity_kg,
       status, created_at)

offer_lots(offer_id FK, lot_id FK, quantity_allocated_kg)   -- multi-lot support

transactions(id, offer_id FK, amount_paise, razorpay_order_id,
             payment_status, created_at)

transaction_events(id, transaction_id FK, event_type, payload JSON, created_at)
             -- append-only audit trail, replaces "blockchain ledger" idea

logistics_providers(id, name, type[storage|transport], lat, lng,
                     capacity_kg, contact)

disputes(id, transaction_id FK, raised_by, reason, status, created_at)

batch_lot_members(batch_lot_id FK, source_lot_id FK, quantity_contributed_kg)

price_forecasts(id, mandi, commodity, date, p10_paise, p50_paise, p90_paise,
                 forecast_confidence, generated_at)   -- cache; confidence
                 -- field feeds the refusal ("NO_ADVICE") logic

-- Tier 3 (stretch) tables — only needed if voice/calling gets built
call_sessions(id, offer_id FK, farmer_user_id FK, buyer_user_id FK,
              provider_session_id, status, started_at, ended_at)
voice_interactions(id, user_id FK, audio_ref, transcript, language,
                    intent_detected, created_at)
```

**Every seeded/generated table (`buyer_demand`, `logistics_providers`) gets a `source` field** (`'real'` or `'demo'`) so the UI can show the honesty badge discussed earlier — add `source VARCHAR` to those two tables.

---

## 3. Complete API Contract

### Core (Tier 1/2 — build these first, in this priority order)

| Endpoint | Method | Notes |
|---|---|---|
| `/auth/register`, `/auth/login` | POST | JWT includes `user_id`, `role` |
| `/users/me` | GET | Reads from JWT, never from a query param |
| `/mandi-locations` | GET | Seeded list |
| `/lots` | POST | Auto-calls Price Engine for band |
| `/lots/{id}` | GET | **Must check requester owns it or is the matched buyer — else 404** |
| `/lots?farmer_id=` | GET | `farmer_id` is derived from JWT, not accepted as a client-supplied filter for other users' data |
| `/lots/{id}/self-assay` | POST | Farmer's structured quality answers → grade |
| `/lots/{id}/price-suggestion` | GET | Band + sale-window text |
| `/lots/{id}/matches` | GET | Matching Engine output |
| `/demands` | POST/GET | Buyer demand posting |
| `/demands/{id}/matches` | GET | **Multi-lot combination** result |
| `/offers` | POST | `{buyer_id, lots: [{lot_id, quantity_allocated_kg}], offered_price_paise_per_qtl}` |
| `/offers/{id}` | PATCH | Accept/reject — ownership-checked |
| `/transactions/{offer_id}/create-order` | POST | Razorpay test order |
| `/transactions/webhook` | POST | Payment confirmation |
| `/transactions/{id}` | GET | Status + event history |
| `/logistics?lat=&lng=` | GET | Nearby options, `source` badge included |
| `/disputes` | POST/GET/PATCH | |
| `/fpo/aggregate` | POST | `{lot_ids: []}` |
| `/ai/price-forecast?mandi=&commodity=` | GET | Raw quantiles for charts |
| `/ai/sale-window?lot_id=` | GET | Returns advice **or** `NO_ADVICE` + reason |

### Tier 3 — Voice & Calling (stretch, build only after freeze)

| Endpoint | Method | Notes |
|---|---|---|
| `/voice/transcribe` | POST (audio) | STT via Bhashini/Sarvam/Google — returns transcript + detected intent |
| `/voice/narrate` | POST | Text → speech audio in user's `preferred_language`, used for reading out sale-window advice |
| `/calls/initiate` | POST | Creates a `call_sessions` row, returns Agora/ZegoCloud token for both parties |
| `/calls/{id}/end` | PATCH | Marks session ended, logs duration |

---

## 4. AI Pipelines — Detailed

### 4.1 Price Engine (reuse, Tier 1)
Load exported TFT + LightGBM artifacts at backend startup. `predict(mandi, commodity, date) → {p10, p50, p90, confidence}`. No retraining — this is your validated, already-built asset.

### 4.2 Sale-Window + Refusal Engine (new logic, Tier 1 — your strongest differentiator)
```
1. Pull p10/p50/p90 for next 14 days for this lot's crop/mandi
2. Compute band width = (p90 - p10) / p50
3. IF band width > threshold (e.g. 25%):
     return NO_ADVICE + reason ("forecast too uncertain for this crop/mandi right now")
4. ELSE:
     compute expected_gain = (p50_future - p50_today) × quantity
                              − transport_cost − commission − storage_cost − spoilage_estimate
     compute worst_case = (p10_future - p50_today) × quantity − same_costs
     return { recommendation: SELL | HOLD, expected_gain, worst_case, itemised_costs }
```
This is the whole "we pay the farmer to wait, or say we don't know" narrative from earlier — implement it exactly like this, it's simple logic on data you already have.

### 4.3 Grading Engine (Tier 1: self-assay; Tier 2: photo CV as second signal)
- **Tier 1 (build this):** Farmer answers ~6 questions (size uniformity, color uniformity, sprouting/damage %, moisture, foreign matter) → rule engine maps answers to Grade A/B/C + one improvement tip. Deterministic, offline-capable, no training needed, no dataset-mismatch risk.
- **Tier 2 (only if time allows):** Photo stored as buyer-facing evidence. A CV model is *not* part of the grading decision in this prototype — don't spend AI-person hours training one under this timeline; it was already flagged as domain-mismatched with fresh/rotten datasets.

### 4.4 Matching Engine (Tier 1)
Greedy scoring: rank available lots by crop match, grade match, proximity (haversine on `lat`/`lng`), and price fit. For a buyer demand exceeding any single lot's quantity, keep adding top-ranked lots until the requested quantity is covered — this produces the multi-lot combination result.

### 4.5 Voice/Language Engine (Tier 3, stretch)
**Scoped-down version — build this, not the full pipeline:**
```
Sale-window advice text (already generated by 4.2)
        │
        ▼
  Translate to farmer's preferred_language (if not already)
        │
        ▼
  Text-to-Speech via Bhashini (primary) / Sarvam (alt) / Google Cloud TTS (fallback)
        │
        ▼
  Audio returned to app, played on a "🔊 Listen" button next to the advice
```
This alone gets you a real, working, demo-able "we support vernacular, voice-first farmers" feature in ~2-3 hours, using a real government API (Bhashini) if it onboards smoothly — a strong point to say out loud to a state-government panel.

**Do not attempt full voice-driven lot creation (STT → form fill) unless the TTS piece above is done with hours to spare** — STT + intent parsing is a meaningfully bigger lift (audio quality issues, background noise in a field, language detection) and is a worse time trade than it looks.

### 4.6 Call Signaling / Negotiation (Tier 3, stretch)
- Use a managed SDK (Agora, ZegoCloud, or 100ms — all have free tiers and React Native/Expo support) instead of raw WebRTC — this turns a multi-day infra problem into an SDK integration.
- On offer acceptance or during active negotiation, either party can tap "Call" → backend issues a session token from the provider, both apps join a voice-only room.
- **Skip "AI negotiation coaching" entirely.** Replace it with: the sale-window band and current offer price shown as a **persistent overlay on the call screen** — the farmer sees "your fair band is ₹1900–2200, current offer is ₹1950" while talking. This delivers almost all the real value (informed negotiation) with none of the live-audio-ML risk.
- Log call metadata (`call_sessions` table: who, when, duration) — useful evidence if a dispute references "we agreed on the call."

---

## 5. Security Non-Negotiables (apply to every endpoint above)

1. **Every query filtering by a user's own data derives the ID from the JWT, never from a client-supplied query parameter.** One FastAPI dependency (`get_current_user`), used everywhere.
2. **Return 404, not 403, for rows the requester shouldn't see** — don't confirm a resource exists to someone unauthorized to view it.
3. **All money fields are integers in paise; all quantity fields are integers in kg** — never float. Format at the UI render edge only.
4. **Razorpay calls happen for real during development/testing, but the live pitch demo runs against a pre-recorded/simulated escrow stepper** if venue wifi is a concern on the day — this is a wifi mitigation, not a trust issue with Razorpay itself.

---

## 6. Team Ownership (final, aligned with your merged plan — Tier 3 slotted in)

| Person | Tier 1/2 ownership (unchanged) | Tier 3 stretch (only after Day 2 Hour 5 freeze) |
|---|---|---|
| **Akash** | Auth + JWT scoping, Lot Engine, self-assay grading, FPO aggregate, DB schema | — |
| **Nikhil** | Price Engine integration, quantiles, Window + Refusal Engine, model card | Voice/Language Engine (owns the API calls to Bhashini/Sarvam — this is API integration work, fits alongside his AI ownership) |
| **Nilesh** | Offers/`offer_lots`, multi-lot matching, escrow, Razorpay, deploy, deck | Call Signaling Engine (Agora/ZegoCloud integration) — only if backend work is fully frozen and stable |
| **Kartik** | Agmarknet ingestion, mandi + WDRA tables, demo dataset, source labelling | Seeds `preferred_language` field, helps test voice narration across languages |
| **Shreya** | Farmer stack: window screen, refusal screen, grade wizard | "🔊 Listen" button wiring, call screen UI (farmer side) if built |
| **Pranay** | Buyer stack, shared components, integration owner | Call screen UI (buyer side) if built |

**Rule: nobody touches Tier 3 until their Tier 1/2 items are done and the Day 2 Hour 5 freeze has happened.** This is what stops the new voice/calling ideas from silently eating time that Tier 1 needs.

---

## 7. Where Tier 3 fits in the existing 2-day schedule

- **Day 1–2, Hours 0–5 (Day 2):** Nobody touches voice/calling. Full focus on Tier 1/2 exactly as previously planned.
- **Day 2, Hour 5 (feature freeze):** Full team checks in. Only if Tier 1/2 is demo-stable does anyone move to Tier 3.
- **Day 2, Hours 5–7 (if Tier 1/2 is stable early):** Nikhil attempts the TTS-only voice slice (§4.5). Nilesh attempts the Agora call integration (§4.6) only if backend is untouched-stable. Both are independently droppable — if either isn't working by Hour 7, cut it from the demo without affecting anything else, since neither touches existing tables/endpoints beyond the two new Tier 3 tables.
- **Day 2, Hour 7–8:** Same as before — final deploy, rehearsal, backup video, deck.

---

**Bottom line:** the voice AI and negotiation-calling ideas are good and worth having on the roadmap slide regardless of whether they make it into the live demo. The architecture above makes them strictly additive — new tables, new endpoints, no changes to anything already built — so attempting them Day 2 evening carries zero risk to the core submission if they don't finish in time.