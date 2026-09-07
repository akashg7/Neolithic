Mandi-Setu — Complete Product Vision
Strengthening Market Linkages and Price Discovery for Farmers
SIH 2026 · PS 26132 · Government of Maharashtra
1. Executive Summary

Mandi-Setu is a market-intelligence and transaction platform for Maharashtra's farmers, built around one core insight: the binding constraint on farmer price realisation is not information — it is the ability to wait.

Farmers already often suspect prices will rise after harvest. They sell anyway because they need cash immediately, have nowhere to store their crop, and have no way to verify a distant buyer will actually pay. Every existing "solution" in this space treats this as an information problem and stops at a price dashboard. We treat it as what it actually is: a liquidity, trust, and logistics problem — and we build for that.

One-line thesis: Everyone will show a price forecast. We're the only ones who turn that forecast into money a farmer can act on today, and the only ones honest enough to say "we don't know" when we don't.

2. The Problem, Properly Decomposed
2.1 Five distinct loss mechanisms (not one)
#	Mechanism	What it actually is
1	Information asymmetry	Farmer knows one price (his own mandi, today). Trader knows several (nearby mandis, direction of travel, forward view).
2	Liquidity coercion	Farmer needs cash now (debt, storage constraints) and sells regardless of whether prices are about to rise. This is the most important and least-served mechanism.
3	Fragmentation / weak bargaining power	One smallholder against a licensed trader has no leverage. Aggregation (FPOs) is the known fix, but FPOs fail without a transparent way to split proceeds fairly.
4	Physical loss (post-harvest)	Produce rots waiting for a truck, a buyer, or a decision. Some loss is a price-information failure, not a cold-chain failure (a farmer who won't harvest because the price doesn't cover picking cost has taken 100% loss from market failure).
5	Counterparty risk	Payment delays, post-facto quality disputes, outright default. This is a tax on every other improvement — a farmer will rationally choose a known local trader who pays cash at a lower price over a distant buyer offering more, because the higher price isn't credible.
2.2 Why a price dashboard fails this problem statement

A dashboard shows a farmer what he already suspects and changes nothing. The actual chain of causation is:

Small holding + cash crop + existing debt
   → no ability to wait → forced sale on harvest day
   → distress price << fair price → debt doesn't clear
   → borrow again, worse terms → next season, even less ability to wait

This is a ratchet, not a static gap. The intervention doesn't need to close the whole gap — it needs to break the ratchet once, by giving the farmer the ability to wait even a single season.

3. Product Thesis and the Five Pillars
3.1 The one sentence

A market-intelligence and transaction layer that tells a farmer WHEN to sell, FINANCES their ability to wait, AGGREGATES their lot for bargaining power, GRADES it so it can be sold at distance, GUARANTEES the payment, and PROVES — with a real measured number — how much the farmer actually gained.

3.2 The five pillars
Pillar	What it is	Loss mechanism addressed
1. Price Intelligence	Multi-mandi price aggregation, localised trends, calibrated multi-day forecasts with honest uncertainty bands	Information asymmetry
2. Sale-Window + Pledge Credit	Converts the forecast into a Hold/Sell decision net of real costs, and — when it says Hold — offers cash today against the stored crop, so the advice is actually actionable	Liquidity coercion
3. Lot, Grade & Aggregation	Digital lot creation, self-assay grading, FPO pooling with a transparent grade-weighted split	Fragmentation
4. Verified Buyer Marketplace + Settlement	Buyer verification tiers, reliability scoring (including renegotiation rate), digital offers with counter-negotiation, escrow-based payment tracking, dispute resolution	Counterparty risk
5. Realisation Ledger	Per-transaction record of what the farmer actually got vs. what they would have gotten selling on harvest day at their default mandi — the proof layer	Makes every other pillar accountable
4. Why "Advice Without Liquidity Is Worthless" — The Core Differentiator

Every competing team will build Pillar 1. Almost none will build the credit loop. The reasoning:

Telling a farmer "hold, prices will rise" when he owes a moneylender by Friday is not just unhelpful — it can be actively harmful, because it invites him to ignore correct advice out of necessity, or worse, follow it and suffer if the forecast is wrong.
The fix already exists as regulated government infrastructure: e-NWR (electronic Negotiable Warehouse Receipts). A farmer stores crop in a WDRA-registered warehouse, receives a receipt, and can pledge that receipt for a partial advance (commonly ~70% of assessed value) from a lender — repaid automatically when the crop eventually sells.
We are not building a lending business. We compute whether using this existing mechanism leaves the farmer better off, and only surface the option when it does. The guardrail is enforced in code, not just suggested in the UI: a pledge offer is never shown unless the expected gain from waiting exceeds the interest cost.
Every surface carries the label: "Indicative simulation — not a lender quote." No specific interest rate or loan-to-value percentage is ever presented as fact until independently verified against WDRA's actual published terms.

The line: "We don't tell farmers to wait. We pay them to wait."

5. The Middleman Question — Our Actual Position
5.1 What a middleman actually is (and isn't)

A middleman is a problem because of opacity + forced bundling + no accountability — not because logistics costs exist. Transport and storage costs are real. The question is who controls them and who can see them.

5.2 Our position: we calculate, we never provide

We are never a transporter, never a warehouse operator, and never a lender. We:

Itemize every cost between farm-gate and buyer (transport, mandi commission, loading, storage, spoilage) so both sides see exactly why a price is what it is
List transport and storage providers as a seeded/registry reference (name, rate, capacity) — a comparison, never a dispatch
Let either side override any cost-line item if they have their own arrangement — the system recalculates, never forces a choice
5.3 The honest complication we resolved: sometimes the middleman genuinely wins

Transparency alone does not make our platform cheaper. A middleman with a full truck, standing relationships, and bulk warehouse rates has real efficiency, not just extraction. Our answer is not to hide this — it's to:

Compete on the same economics, not against them: FPO pooling and cross-lot load consolidation exist specifically to replicate a trader's full-truck economics on behalf of farmers, not just for bargaining leverage
Show both numbers honestly, side by side — "Local trader: ₹980/qtl net. Via platform: ₹940/qtl net → we recommend the local trader today." A platform that only ever recommends itself gets distrusted within a week. One that's occasionally honest about losing becomes the thing a farmer checks every time.
Compete on dimensions beyond price where we can genuinely win even at equal price: certainty (a locked digital offer vs. a trader's word), payment reliability, and reach to buyers a local trader has no relationship with
Even "just checking the app" has value — a farmer who sees a distant market's price and uses it to negotiate harder with his usual trader has extracted value from the platform without a single transaction occurring on it
6. Payment Tracking — Decoupled From Cost Estimation, By Design
6.1 The clean separation

Two entirely different jobs, deliberately never mixed:

Job	What it is	When it matters
Cost breakdown (informational)	An estimate shown before any deal — farm-gate price minus estimated transport/storage/commission = estimated landed price	Helps both sides negotiate a fair number
Payment tracking (transactional)	Tracking whether the money that was actually agreed has moved	After an offer is accepted — has nothing to do with the earlier estimate anymore
6.2 Why this resolves the "what if our estimate is wrong" problem

Once a price is agreed (via the digital offer/counter-offer flow), that agreed number is what gets tracked — never our earlier estimate. Delivery terms (who arranges transport — buyer pickup vs. farmer delivery) are declared as part of the offer, exactly like standard commercial trade terms. Any variance between our estimate and actual logistics cost is a private matter absorbed by whichever party arranged that leg — same as it already works informally today. We are never in the business of adjusting a paid amount after the fact based on logistics.

6.3 The payment tracking feature itself

A simple, auditable status stepper on the agreed transaction amount:

Offer Accepted → Payment Pending → Payment Held (escrow) → Goods Delivered → Payment Released
                                                          ↘️ Disputed → Resolved (farmer/buyer/split)

Every transition is logged append-only (never edited or deleted) — this is what makes the audit trail a genuine trust artifact rather than a claim.

7. The AI / Forecasting Engine
7.1 What makes our forecast different

Three deliberate choices, all defensible under questioning:

We predict an interval, not a number. A single point forecast for a commodity that can move 40% in a week is not intelligence — it's a guess with a chart on it. We predict a low estimate, a likely estimate, and a high estimate (p10/p50/p90) for each of the next 14 days.
We measure the interval, not just claim it. We report MASE (are we better than a naive "same as last week" guess?) and empirical coverage (when we say "80% confident," is the real outcome actually inside our range about 80% of the time?). Both numbers are published honestly — even when unflattering — rather than replaced with a fabricated "accuracy %" figure.
We let the model refuse. When the predicted range is too wide to act on responsibly, the system returns a designed refusal (NO_ADVICE) with a plain-language reason, rather than forcing a confident-sounding but unreliable recommendation. A wrong "hold" costs a farmer real money on a real crop.
7.2 Why LightGBM, not deep learning

Per-series data (one crop, at one specific market) realistically runs into the hundreds to low thousands of rows — nowhere near enough for a deep sequence model (LSTM/Transformer) to learn robust patterns without simply memorizing noise. LightGBM with a quantile objective directly optimizes for honest conditional percentiles, trains in seconds even across many small models, and — critically — can be explained simply and defended under questioning. Model complexity is not the differentiator; measured honesty is.

A single-day forecast requires ~42 small models (14 future days × 3 quantile estimates each) per verified commodity-market group — cheap to train, but each one is real and separately validated.

7.3 Why the training strategy is "pooled by commodity," not "one model per single market"

Rather than training an isolated tiny model per single (crop, mandi) pair using only that pair's thin data, we train one model per commodity using data pooled across multiple markets, with market identity and geographic coordinates (already present in usable datasets) as input features. This gives every market — especially thinner ones — the benefit of patterns learned across the whole commodity, while still producing a market-specific answer at prediction time.

7.4 Why we scope deep AI verification to two commodities (not all)

This is a data-honesty decision, not a shortcut:

Real agricultural price datasets are almost always extremely imbalanced — a small number of high-volume commodities account for the majority of records, while most remaining commodities individually have too little data (often only a few hundred rows statewide, and sometimes only tracked from a much more recent date) to responsibly train and backtest against.
Forcing a forecast out of insufficient data doesn't just waste effort — it actively produces confident-looking but unreliable numbers, undermining the exact "we refuse to guess" positioning that differentiates the product.
We deliberately select two commodities that behave oppositely — one genuinely volatile (onion), one comparatively stable (soybean/similar) — because showing the same refusal-threshold logic produce the correct, different outcome on each proves the system is reacting honestly to real data, not tuned to fake a demo.
Full breadth is preserved elsewhere in the product: any commodity can still be listed, browsed, and traded through the marketplace (lot creation, buyer matching) — it simply doesn't carry a deep AI verdict until it has been genuinely verified. The honest state for an unverified commodity is "detailed advice not yet available for this crop," never a fabricated confident number.
This scoping is explicitly an artifact of what's currently verified, not a permanent ceiling — expanding to additional commodities/markets is a repeatable data-verification process, not a redesign.
7.5 The backtest — proving the forecast, not just claiming it

Using an expanding-window walk-forward method (never a random split, which would leak future information into training and produce a fantastic-looking but meaningless result): for many historical points in time, the model is retrained using only data available up to that point, a forecast is generated, and then compared against what actually happened on that real historical date. Run across hundreds of such points, this produces:

A real MASE score against a genuine baseline
A real coverage percentage, proving whether the claimed confidence band is honest
A visual "predicted vs. actual" chart spanning real history — independently checkable by anyone in the room, since those dates have already happened
7.6 The decision layer (not machine learning — deterministic arithmetic)

Once a forecast exists, a separate, fully deterministic layer converts it into an actionable verdict:

Subtract real, itemized costs (transport, commission, loading, storage, spoilage) from every possible sale day
Compare selling today vs. every future day within the forecast horizon
Refuse to advise if the range is too uncertain, if there isn't enough history, if the data is stale, or if the expected gain doesn't clear the cost/risk of waiting
Otherwise decide: Sell Now / Sell at a different (better net) market / Hold / Split (sell half now, hold half — mirroring what an experienced trader already does when both real upside and real downside exist)
The worst-case outcome is always computed and always shown at equal visual weight to the best case — this is a structural rule, not a UI suggestion, and it's what makes the "honesty" claim real rather than rhetorical
7.7 No generative AI in the advice path — deliberately

An LLM that could hallucinate a confident "hold for 12 days" recommendation would directly invert the entire product thesis, which is built around refusing to overclaim. Any conversational/FAQ assistance in the product is retrieval-based over a fixed, curated set of answers — never free-form generation used for financial advice.

8. Voice Interface
8.1 Why voice is core, not decorative

A large share of the actual target users (low-literacy smallholders, often women, who do much of the agricultural labor) cannot reliably read a price chart or a rupee figure. Voice is the primary interface for the moments that matter most — not a checkbox accessibility feature retrofitted at the end.

8.2 Where voice is used (and deliberately, nowhere else)
Screen	Direction	What happens
Registration	Out + In	One question asked aloud at a time, farmer answers, field pre-fills, final confirmation screen before submission
Verdict screen ⭐	Out	Reads the Hold/Sell decision and the rupee amount aloud
Refusal screen	Out	Reads the specific reason the system is declining to advise
Pledge card	Out	Reads the loan amount, interest, and total repayment aloud
Grading questions (×6)	Out	Each self-assay question read aloud
Lot creation	In	Farmer speaks crop/quantity/mandi, form pre-fills
8.3 The non-negotiable rule

Voice never commits anything. It only ever pre-fills a form or reads information aloud. Every action that creates a record or moves money requires an explicit human tap to confirm — no exceptions, including registration.

8.4 How it's technically built for reliability
Voice-out audio is generated via a text-to-speech provider, but critically not called live during a demo or in an unreliable-connectivity moment — sentences are pre-generated and cached, so replaying an already-heard message never requires a new network call, and the rehearsed core flows can work fully offline.
Voice-in (speech recognition) inherently requires a live connection at the moment of speaking — this is an accepted, explicit gap, always paired with a graceful fallback to manual typing so the form is never blocked by a network hiccup.
A provider fallback ladder exists (primary provider → free government-provided alternative → on-device fallback → manual text entry) so voice degrades gracefully rather than breaking the app.
9. Trust, Verification, and Aggregation
9.1 Buyer verification tiers

Buyers move through verification levels (unverified → identity-checked → track-record-verified) with escalating transaction limits and trust signals, so a farmer can see exactly how much a counterparty has actually been checked rather than a single opaque "verified" badge.

9.2 The renegotiation rate — the metric nobody else shows

Alongside deals completed and on-time payment percentage, we surface how often a given buyer has tried to lower the agreed price after delivery on a quality pretext. This is a classic, well-documented trader abuse pattern, and making it visible — before a farmer accepts an offer — is real trust infrastructure most platforms omit entirely.

9.3 FPO grade-weighted aggregation

Small farmers' lots are pooled into one larger, buyer-attractive batch. Each contributing farmer's share is calculated as quantity × a grade-based multiplier, and — critically — every member sees their own projected share and the exact formula behind it before consenting to pool. A pool that would leave any member worse off than selling alone simply does not form. This turns "we support FPOs" from a slogan into a specific, auditable mechanism that prevents the disputes that typically break producer collectives.

9.4 Counter-offer negotiation with data-backed leverage

Rather than a take-it-or-leave-it accept/reject flow, a farmer can counter a buyer's offer — and critically, the counter screen shows the farmer's own forecast right next to the input box ("Buyer offered ₹1,900. Your forecast says ₹2,050 achievable in 11 days."). This hands the farmer exactly the informational advantage a middleman traditionally holds.

9.5 The Realisation Ledger — the proof layer

Every completed transaction is recorded against a counterfactual baseline (what the farmer would have received selling at their default mandi on harvest day), producing a real, auditable "rupees gained" figure per transaction and in aggregate. This is stored append-only (never editable), giving the product — and eventually the state government — a genuine measurement instrument rather than a marketing claim.

9.6 Data provenance, always visible

Every price point and every screen showing real numbers carries a visible source label (e.g., government market data vs. seeded demonstration data). This is volunteered proactively, not something a user has to dig for or ask about — because presenting demonstration data as real government data, even by accident, is treated as the single most damaging mistake the product could make in front of any official evaluator.

10. Complete Feature Set — Organized by Maturity
🟢 Core (built and demonstrable)
Multi-mandi price aggregation with source labeling
Calibrated 14-day forecast with honest uncertainty bands, for verified commodities
Sale-window verdict (Sell Now / Sell Elsewhere / Hold / Split / honest refusal)
Itemized, transparent cost breakdown (transport, commission, storage, spoilage)
Pledge-finance simulation, guarded so it never suggests an unworthwhile loan
Lot creation with self-assay grading (photo attached as evidence, not as the classifier)
Buyer demand posting and ranked matching, including multi-lot combination fulfillment
FPO grade-weighted pooling with pre-consent transparency
Digital offers with counter-negotiation (forecast shown alongside the counter input)
Buyer verification tiers + reliability score including renegotiation rate
Escrow-style payment status tracking on the agreed transaction amount
Dispute raising with evidence and status tracking
Data provenance screen
Marathi-first UI with full voice-out on key decision moments and voice-in on lot creation
🔵 Near-term roadmap (credible, sequenced next steps)
Real photo-based computer-vision grading as a second, cross-checked signal
Real buyer KYC (GST/business registration verification)
Real payout rails to farmer bank/UPI accounts
Real logistics provider network with live booking (beyond the current seeded lookup)
Live, daily-refreshed price ingestion (beyond the current periodic import)
Admin dispute console with SLA-based escalation
Additional verified commodities, following the same rigorous data-verification process
Additional languages beyond Marathi/English
SMS/IVR fallback for non-smartphone farmers
⚪ Longer-term vision
Real integration with formal government credit schemes (e-NWR lenders, NABARD) as the underlying credit line, replacing the current simulation
Participation as an interoperable node on India's open commerce network (ONDC), rather than a closed platform
A government-facing policy dashboard — anonymized, aggregated market intelligence at district/state level
Weather-integrated forecasting and explicit modeling of policy shocks (export bans, minimum export prices)
Cross-market arbitrage optimization and per-farmer risk-tolerance personalization
11. Complete Screen Inventory (Product Surface)

~26 screens across a farmer stack and a buyer stack, one shared codebase:

Onboarding (3): language picker, phone/OTP, profile setup
Farmer home (1): dashboard with today's price, offline-aware banner, single primary "hold or sell?" action
Price discovery (4): price history, net-of-transport nearby mandi comparison, 14-day forecast, model card
Core decision (2): the verdict screen (hero), cost breakdown
Liquidity (1): pledge simulation card
Lot & grading (2): create lot, 6-question self-assay
Farmer marketplace (3): offers + counter-negotiation, transaction timeline, FPO pool view
Buyer stack (7): login, post demand, ranked matches, make offer, offer thread, transaction timeline, lot detail
Trust & transparency (3): data provenance, buyer reliability card, dispute flow

Every screen carries: a language toggle, a data-source badge where relevant, and defined empty/loading/error states — nothing is allowed to look silently broken.

12. What We Deliberately Do Not Do (and why it strengthens the product)
We never take a position on produce. We are not a buyer, and our incentives are never entangled with the price outcome — this is the foundation of the "neutral infrastructure" claim.
We never lend from our own balance sheet. We compute whether an existing, regulated credit mechanism is worth using — we don't originate credit ourselves.
We never sell inputs. This avoids the same conflict-of-interest structure that makes many existing agri-advisory apps untrustworthy on price.
We never claim confidence we haven't measured. Every forecast carries a real, checkable accuracy measurement; every refusal is a designed feature, not an error state.
We never present demonstration data as government data, under any framing or time pressure.
We never let voice commit money or create a permanent record without an explicit human tap.
13. Why This Wins, Summarized

Most competing approaches to this problem statement will converge on the same shape: a price dashboard, a basic buyer marketplace, a simulated payment flow. That is table stakes, not differentiation.

What sets Mandi-Setu apart is the combination, not any single piece:

A forecast that admits uncertainty and refuses when it should
A financing mechanism that makes "wait for a better price" an actually followable instruction instead of empty advice
A cost structure that competes with informal middlemen honestly — including admitting when they're currently the better option
A negotiation flow that hands the farmer the information advantage a trader used to hold alone
A ledger that proves, transaction by transaction, that the farmer actually gained — turning a promise into a measured, auditable fact

The synthesis is the product. No single pillar here is unprecedented in isolation — the reason this stands apart is that most solutions stop at pillar one, and we built the whole loop.