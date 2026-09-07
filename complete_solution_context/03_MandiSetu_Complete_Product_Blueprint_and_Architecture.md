# MANDI-SETU
## The Farmer Price Realisation Platform
### Complete Product Vision — Prototype to Production

**Problem Statement:** SIH 2026 · PS 26132 · Strengthening Market Linkages and Price Discovery for Farmers
**Organisation:** Government of Maharashtra · Maharashtra State Innovation Society
**Category:** Software · Theme: Agriculture, FoodTech & Rural Development

---

## PART 1: THE PROBLEM AND OUR THESIS

### 1.1 The Problem, As Stated

Smallholder farmers and FPOs across Maharashtra have limited visibility into current and expected prices across nearby markets, processors, and institutional buyers. Information on quality specifications, demand, logistics, storage, payment reliability, and buyer credentials is fragmented. Farmers often sell immediately after harvest due to liquidity or storage constraints, with weak bargaining power. Buyers struggle to source consistent, quality-verified volumes.

### 1.2 The Deeper Truth We Build Around

Most solutions to this problem stop at "give farmers price information." We believe this misses the actual mechanism of harm.

**A farmer often already suspects prices will rise after harvest.** He sells anyway — not because he lacks information, but because he cannot afford to wait. A trader advanced him money in planting season. His daughter's school fee is due. He has nowhere to store forty quintals of onion. The debt must clear this week, not in eleven days when the price is better.

**Maharashtra recorded the highest number of farmer suicides of any Indian state in recent years.** Debt and price collapse are the two most-cited contributing factors. A farmer who cannot wait sells into the very price glut he is helping create.

**Our thesis: the binding constraint is not information. It is the ability to wait.**

This single reframing changes what we build. A price dashboard answers a question the farmer already suspected the answer to. A system that gives him the *means* to act on good information — cash today, without selling today — answers the question that actually matters.

### 1.3 One-Line Description

> *Everyone building for this problem will show a price forecast. We are the only team that turns that forecast into money a farmer can act on today — and the only one honest enough to say "we don't know" when we genuinely don't.*

---

## PART 2: THE FIVE ROOT-CAUSE MECHANISMS

We do not treat "farmers earn less than they should" as one problem. It is five distinct, separately-caused problems, and each needs its own fix.

| # | Mechanism | What it means | Our fix |
|---|---|---|---|
| 1 | **Information asymmetry** | The trader knows tomorrow's likely price trend; the farmer only knows this morning's shout price at one mandi | Multi-mandi price board, net of transport, plus a calibrated 14-day forecast |
| 2 | **Liquidity coercion** | Farmer sells at harvest not because the price is fair, but because he cannot wait for a better one | Sale-window verdict bundled with pledge-finance — cash today against stored crop, only offered when it's genuinely worth it |
| 3 | **Fragmentation / weak bargaining power** | A single farmer with 8 quintals has no leverage against a trader with volume and alternatives | FPO pooling with a transparent, grade-weighted, pre-consented split; direct farmer-buyer counter-negotiation backed by the farmer's own forecast |
| 4 | **Physical/post-harvest loss** | Crop rots waiting for a buyer, or is dumped because the price doesn't cover harvest cost | Grade-differentiated routing (a lot that fails fresh-market grade still has value to a processor); storage-aware sale-window timing |
| 5 | **Counterparty risk** | Payment delays, post-delivery price renegotiation, buyers who never pay | Buyer verification tiers, a reliability score that specifically tracks renegotiation rate, escrow-based settlement, structured dispute resolution |

**The insight that ties these together:** these five mechanisms compound into a ratchet. A bad season increases debt, which reduces the ability to wait next season, which produces a worse sale, which increases debt further. Breaking this loop even once — giving a farmer the ability to wait through a single bad season — changes the trajectory of every season after it.

---

## PART 3: THE PRODUCT — FIVE PILLARS

### Pillar 1: Price Intelligence
Multi-mandi price aggregation with real government price data (Agmarknet), arrival volumes as a supply signal, and a calibrated 14-day price forecast expressed as a range (low/likely/high) rather than a single misleadingly-confident number.

### Pillar 2: Sale-Window Decision + Pledge Finance
The forecast alone changes nothing. This pillar converts it into an actionable verdict: **Sell Now / Sell Elsewhere / Hold / Split**, computed by netting real costs (transport, commission, storage, spoilage) against the forecast. When the verdict is Hold, the system simultaneously offers a **pledge-finance simulation** — cash today against the stored crop, via the existing e-NWR (electronic Negotiable Warehouse Receipt) government mechanism — but **only when the expected gain from waiting genuinely exceeds the interest cost.** This constraint is enforced in code, not merely suggested in the interface.

Critically, this pillar also **refuses to advise** when the forecast is too uncertain to act on. This is a designed feature, not an error state — a wrong "hold" recommendation costs a farmer real money on a real crop, and the honest answer is sometimes "we don't know."

### Pillar 3: Lot, Grade & Aggregation
Digital lot creation, a deterministic six-question self-assay grading system (photo attached as supporting evidence, not as the classifier itself), and FPO pooling with a **grade-weighted, pre-consented fair-split** — every member sees their exact share and the gain versus selling alone, before agreeing to pool.

### Pillar 4: Verified Buyer Marketplace & Settlement
Tiered buyer verification, ranked matching (including multi-lot combinations that fill a single large buyer order from several smaller farmer lots), direct counter-offer negotiation where the farmer sees his own forecast beside the buyer's offer, an escrow-based settlement state machine, and structured dispute resolution.

### Pillar 5: Realisation Ledger (The Proof Layer)
For every transaction, we record what the farmer actually received against a counterfactual baseline (what he would have received selling at his default mandi on harvest day). This produces a genuine, measurable number: **rupees per quintal gained**, backed by an append-only, tamper-evident record. This is the pillar that turns "we help farmers earn more" from a claim into evidence.

---

## PART 4: THE AI/FORECASTING ENGINE — HOW AND WHY

### 4.1 What We Predict, and Why Not a Single Number

We forecast a **range** — a low estimate (p10), a likely estimate (p50), and a high estimate (p90) — for each of the next 14 days, rather than a single price. A single-number forecast for a commodity as volatile as onion is a guess wearing a chart. A range with honest, measured confidence is intelligence.

### 4.2 The Model: LightGBM Quantile Regression

We use **LightGBM** (a fast, tree-based gradient-boosting algorithm) with a `quantile` objective, training three separate models per future day — one for each of the low/likely/high estimates — across a 14-day horizon. This produces 42 small models per commodity-market series.

**Why not a deep learning model (LSTM, Transformer, TFT)?** Deep learning models require large amounts of data *per series* to avoid overfitting, and are difficult to explain in a live setting. When we examined our actual dataset — 240,679 records across 129 commodities and 367 mandis — the *aggregate* size looked large, but the *per-series* size (one specific crop at one specific mandi) was frequently only a few hundred rows. At that scale, a deep model would memorize noise rather than learn a genuine pattern, take significantly longer to train, and be far harder to defend under technical questioning. LightGBM's quantile objective directly optimises for honest, calibrated intervals and trains in seconds — the right tool for this data reality, not a compromise forced by time pressure.

### 4.3 How We Prove the Forecast Is Honest (Not Just Claimed)

This is the centrepiece of our technical credibility, and it works as follows:

**Walk-forward backtesting.** We simulate the model's real-world behaviour by stepping through history: at each point in the past, we train only on data available *up to that point*, generate a forecast, then compare it against what *actually* happened — repeated across hundreds of historical instances. Critically, the model is never shown the future at the moment it makes each prediction, which is what makes this test honest rather than a leak.

We report exactly two measured numbers, both computed this way and neither invented:

- **MASE (Mean Absolute Scaled Error)** — our error, scaled against a seasonal-naive baseline (simply guessing that today's price equals the price seven days ago, which captures mandi prices' weekly rhythm). A MASE below 1.0 means we genuinely beat a real, honest baseline. If our MASE is not below 1.0, we say so directly rather than fabricating a better number — this honesty is itself part of the pitch.
- **Coverage** — of all the times we predicted an 80% confidence range, what percentage of the time did the actual price genuinely fall inside it? A number close to 70–90% means our stated confidence is trustworthy; far outside that range means our "confidence" is decorative.

Both numbers are persisted into a **model card** — a permanent, viewable record in the product itself (not just a slide) that also names the model's **known limitations** honestly (e.g., no weather features yet, does not model sudden policy shocks like export bans). Naming a model's blind spots before being asked is what makes its stated strengths believable.

### 4.4 Why We Deeply Verify Only Two Commodities (Not All 129)

Our dataset contains 129 commodities, but the data is extremely unevenly distributed: roughly the top 15 commodities account for the large majority of all records, leaving well over 100 commodities sharing a small fraction of the data — often only a few hundred rows *for the entire state*, which becomes a few dozen rows or fewer once narrowed to a single mandi. Additionally, only 10 commodities were tracked from the start of our data's timeline; the remaining commodities only entered the dataset in later periods, meaning many have genuinely limited historical depth regardless of their total row count.

Training and — critically — *honestly backtesting* a model requires a minimum amount of real, continuous history (we use a 180-row floor). Below this threshold, any forecast is statistically closer to noise than signal, and any backtest result computed from it is not meaningful. Presenting such a result as verified would directly contradict the honesty this entire product is built on.

**We therefore deeply verify two commodities: onion and soybean** — deliberately chosen because they represent opposite real-world cases. Onion is genuinely volatile; our system should — and does — sometimes refuse to advise on it. Soybean is comparatively stable; our system gives it a confident, well-supported verdict. Demonstrating the same refusal logic responding correctly to two opposite real situations is stronger proof of honesty than a longer list of unverified commodities would be.

**This does not limit the product's breadth.** The marketplace (lot creation, buyer demand, matching, FPO pooling) supports all commodities, since these features require only that a commodity exists as reference data — not a trained forecast. Only the AI sale-window verdict is scoped to the two commodities we have genuinely proven; for any other crop, the product is explicit that detailed advice is "not yet available" rather than presenting an unverified guess as fact.

### 4.5 The Decision Layer — Turning Forecast Into Rupees

The forecast alone is not the product; a separate, deterministic (non-machine-learning) decision layer converts it into an actionable verdict:

1. Compute what the farmer nets selling today (spot price minus transport, commission, loading).
2. For each of the next 14 days, compute the net if the farmer holds and sells then (forecast price minus the same costs, plus storage cost and spoilage — the value lost to the crop degrading while stored, which is genuine and often underweighted in naive advice).
3. Select the best day by the median (likely) net outcome.
4. **Check whether the forecast's uncertainty at that chosen day is trustworthy.** If the range between the low and high estimate is too wide relative to the price, the system returns **NO_ADVICE** with a specific, named reason — rather than a shrug-shaped recommendation.
5. If confident, decide the final verdict: sell elsewhere (if a nearby market nets more after transport), sell now (if waiting genuinely doesn't help), split (sell half now, hold half — used when both real upside and real downside exist), or hold.
6. **The worst-case outcome is always computed and always shown, at the same visual weight as the best case.** This is not a UI suggestion — it is a structural rule that makes the honesty claim real rather than rhetorical.

---

## PART 5: TRUST, LOGISTICS AND THE MIDDLEMAN QUESTION

### 5.1 We Are Not the Middleman

A recurring concern in our own design process: if we calculate logistics costs and present a "landed price" to a buyer, are we simply becoming a new, digital middleman? Our answer is structural, not just semantic.

A middleman's power comes from **opacity, forced bundling, and unaccountable pricing** — not from the mere existence of transport and storage costs, which are real and unavoidable. Our approach:

- We show an **itemised cost breakdown** (transport, commission, storage, spoilage) as a transparent estimate, sourced from a registry of transport/storage providers rather than a cost we invent or profit from.
- Either party can override any cost line with their own arrangement, and the total recalculates — we never force a bundled logistics choice.
- We never take a hidden spread. If the platform ever charges a fee, it is a small, fixed, disclosed amount — never an undisclosed markup baked into a price.
- **Payment tracking is entirely decoupled from our cost estimates.** Our cost breakdown is shown *before* a deal, purely to help both sides negotiate a fair price. Once an offer is accepted, whatever price was actually agreed becomes the locked transaction amount — the platform tracks only whether that agreed money moved (Pending → Held → Delivered → Released), and never recalculates it based on logistics variance afterward. This mirrors how any ordinary commercial transaction works: an estimate informs the negotiation; the invoice is whatever was actually agreed.

### 5.2 Honest Competition With Existing Middlemen

We do not assume our platform always beats a local trader on price — sometimes a trader's scale (full trucks, standing relationships, bulk storage rates) genuinely produces a lower cost than we can offer a single small farmer. Rather than hiding this:

- **FPO pooling and multi-lot transport consolidation** exist specifically to replicate the trader's scale advantage on the farmer's behalf, not merely to increase bargaining leverage.
- When our platform's net price is genuinely lower than a known local alternative, **we say so honestly** rather than always recommending ourselves. A platform that only ever recommends itself is quickly distrusted; one that is occasionally honest about not being the best option becomes the tool a farmer checks every time.
- We compete on dimensions beyond price where a trader is structurally weaker: payment certainty, reach to buyers a local trader has no relationship with, and freedom from the informal debt relationships that often quietly force a farmer to sell to a specific trader regardless of price.

---

## PART 6: VOICE AND ACCESSIBILITY

### 6.1 Why Voice Is Core, Not Decorative

Maharashtra's female literacy rate trails male literacy meaningfully, and functional literacy for reading a price chart or a rupee figure is lower still. A significant share of the actual user base of this product may not reliably read Marathi text, let alone English. **Voice is not an accessibility checkbox — it is how the primary user actually receives the product's most important information.**

### 6.2 Where Voice Appears, and the One Governing Rule

Voice output (the app speaking to the farmer) appears on exactly four surfaces: the sale-window verdict, the refusal explanation, the pledge-finance terms, and the six grading questions. Voice input (the farmer speaking to the app) appears in exactly one place: lot creation, where speech pre-fills the form fields.

**The governing rule, with no exceptions: voice never commits anything.** Every voice-filled field must be explicitly confirmed by a human tap before it becomes a real record. This applies even to registration, which we optionally extend to a guided one-question-at-a-time voice flow using the identical pre-fill-then-confirm pattern.

### 6.3 Technical Approach — Reliability Over Convenience

Voice output is generated using natural, full Marathi sentences (via Sarvam's text-to-speech), but critically, these are **generated once, ahead of time, and cached** — never called live during an actual demo or, in production, never depended upon as a live call for fixed, predictable content (refusal reasons, grading questions). This preserves the product's ability to function with no live network connection, which we treat as a non-negotiable requirement given how unreliable rural and venue connectivity genuinely is. Voice input (speech recognition) does require a live call by nature, since it responds to speech that hasn't happened yet — for this, the product always falls back gracefully to manual text entry if the network is unavailable, rather than blocking the user.

---

## PART 7: PROTOTYPE SCOPE — WHAT WE BUILD FIRST

We do not attempt the full vision in the initial build. The prototype is a deliberately narrow, deeply honest slice:

- **Crops:** Onion (Nashik-Ahmednagar belt) and Soybean (Latur belt) — deeply verified, backtested, and model-carded. All other commodities remain listable in the marketplace but without an AI verdict attached.
- **Payments:** An escrow *state machine* in our own database, clearly labelled as simulated — the state machine logic itself is real and fully functional; only the actual movement of money is simulated.
- **Grading:** A deterministic six-question self-assay, with the photo stored as evidence for buyers rather than used as the classifier — computer-vision grading is an honestly-labelled future upgrade, not a Phase 1 claim.
- **Pledge finance:** A clearly-labelled simulation of the real, existing e-NWR government mechanism — we compute whether it is worthwhile, we do not act as an actual lender.
- **No generative AI chatbot.** We deliberately do not ship a free-form conversational assistant that could hallucinate financial advice — this would directly undermine a product whose entire premise is refusing to guess. A retrieval-based (not generative) FAQ assistant is the appropriate Phase 2 addition.

---

## PART 8: THE ROADMAP — WHAT COMES AFTER

| Phase | Timeline | What it adds |
|---|---|---|
| **Phase 2** | 1–3 months | Live daily price ingestion (not a one-time historical load); computer-vision grading as a genuine second signal alongside the self-assay; real KYC-verified buyer onboarding; real payout to farmer bank accounts; real lender integration for pledge finance; a retrieval-grounded (citation-based, refusal-capable) AI assistant; expansion to additional verified commodities as each clears the same honest verification bar as onion and soybean |
| **Phase 3** | Production / state scale | Government policy dashboard aggregating district-level price realisation and FPO health for the Department of Skills, Employment, Entrepreneurship and Innovation; participation as an interoperable node on ONDC (India's open commerce network); SMS/IVR fallback for feature-phone farmers; multi-state expansion, with the entire architecture already parameterised by state so this is a configuration change, not a rebuild |

---

## PART 9: HOW WE MEASURE SUCCESS

Every outcome named in the problem statement maps to a specific, measurable feature in our system — not an aspiration:

| Stated outcome | How we measure it |
|---|---|
| Improved farmer price realisation | The Realisation Ledger's per-transaction gain versus counterfactual baseline, aggregated into a genuine rupees-per-quintal figure |
| Reduced information asymmetry | Forecast reach and measured coverage accuracy, published openly in the model card |
| Lower transaction cost | Itemised cost comparison versus the traditional mandi-and-broker route |
| Stronger FPO aggregation | Average pooled lot size and the transparent per-member gain-versus-solo figure |
| Reduced post-harvest loss | Grade-differentiated routing rate and storage-aware timing outcomes |
| More reliable buyer sourcing | Buyer fill rate and repeat-buyer rate, weighted by the reliability score |
| Transparent transaction records | Completeness of the append-only audit trail, verifiable by any party |

---

## CLOSING STATEMENT

We are not building a price dashboard. We are building the thing a farmer actually needs when he already suspects — correctly — that waiting would earn him more: the ability to wait, the honesty to know when that suspicion isn't well-founded, and the proof, afterward, that it worked.