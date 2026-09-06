# Complete Solution Checklist — PS 26132
### Mapped clause-by-clause to the PS's "Expected Solution" sentence
### For the pitch deck's "Our Complete Solution" / roadmap slide
**Tags: 🟢 Built in 2-day prototype · 🔵 Phase 2 (near-term, 1–3 months) · ⚪ Phase 3 (full production vision)**

---

## Clause 1: "Aggregates mandi prices, buyer demand, quality requirements, arrival volumes, transport and storage options"

- 🟢 Real historical mandi price data ingested from Agmarknet, per crop, per mandi
- 🟢 Real arrival volume data alongside prices (from the same government source)
- 🟢 Buyer demand postings (crop, quantity, grade, price ceiling, location)
- 🟢 Static seeded transport/storage options shown per lot
- 🔵 Live/daily-refreshed mandi price feed (not a one-time historical import)
- 🔵 Real transport provider network (verified local truck/tempo operators, not seeded)
- 🔵 Real cold-storage/warehouse directory (WDRA-registered godowns, live capacity)
- ⚪ Direct data-sharing integration with e-NAM / state APMC systems, so prices update automatically without scraping

## Clause 2: "Provides localised price trends and sale-window recommendations"

- 🟢 Price trend chart (recent history) per crop/mandi
- 🟢 p10/p50/p90 probabilistic 14-day forecast (TFT + LightGBM)
- 🟢 Sale-window recommendation with real ₹ figures: expected gain from waiting, itemised costs (transport, commission, storage, spoilage), and worst-case loss shown at equal visual weight
- 🟢 Refusal logic — system declines to advise ("NO_ADVICE") when the forecast band is too wide to be trustworthy, and says why
- 🔵 Personalization: recommendation adjusted for the specific farmer's known transport distance and typical spoilage rate for their crop
- 🔵 Multi-crop portfolio view for FPOs — sale-window advice across all crops the FPO handles at once
- ⚪ Automated alerts (SMS/push) when a tracked crop crosses a recommended sell/hold threshold

## Clause 3: "Matches farmers/FPOs with verified buyers"

- 🟢 Rule-based matching (crop + grade + proximity + price fit)
- 🟢 Multi-lot combination matching (combine several small lots — including an FPO batch lot — to fulfill one large buyer order)
- 🟢 Buyer profile with a verification flag/badge
- 🔵 Real KYC-based buyer verification (GST number, business registration check, phone/Aadhaar-linked verification)
- 🔵 Buyer trust score built from transaction history (on-time payment, dispute rate) over time
- ⚪ ML-based matching that learns from accepted/rejected offer patterns, not just a static scoring rule

## Clause 4: "Enables lot creation, quality grading, digital offers, logistics coordination, and payment tracking"

**Lot creation**
- 🟢 Farmer/FPO creates a lot: crop, quantity, location, price band auto-suggested

**Quality grading**
- 🟢 Structured self-assay grading (farmer answers observable quality questions → rule-based Grade A/B/C) with a weakest-dimension improvement tip
- 🟢 Photo attached as supporting evidence for the buyer (not the grading input)
- 🔵 Photo-based CV grading as a genuine second signal once trained on real mandi-grading data (not spoilage datasets) — cross-checked against the self-assay, not a replacement for it
- ⚪ Third-party/agent-assisted physical grading integration for high-value lots, recorded on-platform

**Digital offers**
- 🟢 Buyer sends an offer (single-lot or multi-lot); farmer/FPO accepts or rejects
- 🔵 Counter-offer negotiation (not just accept/reject — a back-and-forth price thread)
- 🔵 Offer expiry timers, so lots aren't held hostage by a slow-responding buyer

**Logistics coordination**
- 🟢 Nearby storage/transport shown as information on the lot page
- 🔵 In-app "request pickup/storage slot" — creates a coordination request/ticket to a real registered provider
- ⚪ Live tracking of produce from farm gate to buyer (status updates: picked up → in transit → delivered)

**Payment tracking**
- 🟢 Razorpay test-mode order creation, escrow-style status stepper (Pending → Held → Released), backed by an append-only transaction-events audit log
- 🔵 Real payout-to-farmer leg (Razorpay Payouts or equivalent, to bank/UPI, with real KYC)
- 🔵 **Pledge-finance / warehouse receipt lending:** farmer stores crop in a WDRA-registered warehouse, gets a receipt, borrows a partial advance today against it (e.g. ~70% of assessed value), loan auto-repaid from the eventual sale — **only offered when the expected gain from waiting exceeds the interest cost**, so the system never lends in a way that leaves the farmer worse off
- ⚪ Full integration with formal agri-credit schemes (NABARD, e-NWR-backed lending) as the underlying credit line, rather than a simulated one

## Clause 5: "Supports dispute or grievance processes"

- 🟢 Basic dispute form + status (Open/Resolved) tied to a transaction
- 🔵 Admin console for reviewing and resolving disputes, with evidence attachments (photos, grading records, offer history)
- 🔵 SLA-based escalation (auto-flag disputes unresolved after N days)
- ⚪ Neutral third-party arbitration workflow for high-value disputes, with a formal resolution record

---

## Expected Outcomes — how the complete solution delivers each one

| PS-stated outcome | How the full solution achieves it |
|---|---|
| Improved farmer price realisation | Real-number sale-window advice + pledge-finance removes the "forced to sell cheap" trap |
| Reduced information asymmetry | Aggregated real price/arrival data + buyer demand, all visible to the farmer in one place |
| Lower transaction cost | Digital offers and matching remove layers of informal middlemen/brokers |
| Stronger FPO aggregation | Batch-lot creation + grade-weighted payout splitting makes small lots viable to trade |
| Reduced post-harvest loss | Sale-window timing advice + storage-option visibility reduces distress/rushed selling |
| More reliable buyer sourcing | Verified buyer badges/trust scores + multi-lot fulfillment for large orders |
| Transparent transaction records | Append-only audit log on every transaction, source-labeled data throughout the app |

---

## Cross-cutting features worth naming on the roadmap slide (not tied to one clause)

- ⚪ Multi-language support (Marathi, Hindi, and other regional languages) — critical for real smallholder adoption, currently English/Marathi in the prototype
- ⚪ Low-bandwidth/offline-first mode and SMS/IVR fallback for farmers without reliable smartphone data access
- ⚪ Government/policy dashboard — aggregated, anonymized market intelligence for the Department of Skills, Employment, Entrepreneurship and Innovation to monitor price trends and FPO health at a district/state level
- ⚪ ONDC network participation — positioning AgriSense as an interoperable node on India's open commerce network rather than a closed platform

---

**How to use this slide:** don't present this as "here's what we built" — present it as "here's the destination, and here's exactly how much of it is real today" (🟢 items), with the 🔵/⚪ items framed as a credible, sequenced roadmap. A panel that sees you clearly separating built-vs-planned trusts every 🟢 claim more, not less.