# Backend alignment status — read at `efea078`

**Reviewed:** 2026-09-06 · `akashg7/Neolithic-Backend` @ `efea078acdaec4280e5e6d8ecda60c81c234b164`
**Previous review:** `9137d75` (the one that produced `frontend_doubts.md`)
**Reviewer:** Pranay (frontend), against `app/src/types/api.ts` in this repo.

Everything below cites Akash's files by path. Where I say "ours", I mean
`app/src/types/api.ts` — which, since the four backend/AI members are working in a
separate repo, is the frontend's operative wire contract until merge.

---

## 0. The number, up front

| | Ready |
|---|---|
| **Contract *shape*** — field names, types, enums, envelope, paths | **≈ 75 %** |
| **Contract *behaviour*** — does the response carry usable numbers | **≈ 20 %** |
| **Blended, from the frontend's point of view** | **≈ 45 %** |

The shape moved a long way in one pass. The behaviour did not move, and the hero
endpoint is currently worse than a fixture: it answers every question with
`SELL_NOW`, zero gain, zero worst case, zero costs, and no Marathi sentence.
Section 3 shows why that is arithmetic, not a bug I am guessing at.

**Nothing here blocks our frontend today.** We are on fixtures by design and every
screen is built to be indistinguishable from live. This document is the merge
punch-list, not a stop-work.

---

## 1. What Akash fixed — all five blockers, confirmed at source

| | Was | Now | File |
|---|---|---|---|
| **B1** role casing | `^(farmer\|buyer\|fpo_admin)$` | `^(FARMER\|BUYER\|FPO_ADMIN)$` + a `role_upper` validator on both user schemas | `app/schemas/auth.py` |
| **B2** `id: int` | `UserResponse.id: int` | `id: str` + `id_to_str` validator | `app/schemas/auth.py` |
| **B3** password auth | `POST /auth/login {phone, password}` | `POST /auth/otp/request` → `POST /auth/otp/verify` → `POST /auth/register {…, code}`. Password gone. `bcrypt` hash in `otp_codes`, 120 s TTL, 5-attempt cap, `dev_otp` echoed only outside production | `app/schemas/auth.py`, `app/routers/auth.py`, `app/services/auth_service.py` |
| **B4** error envelope | three different shapes | one `RequestValidationError` handler → 400 and one `StarletteHTTPException` handler, both emitting `{"error": {"code", "message", "field"}}` with a sensible status→code map | `app/main.py` |
| **B5** no `/api/v1` | bare `/auth`, `/lots`, … | every router mounted `prefix="/api/v1/…"` | `app/main.py` |

Also landed unasked and correct: `locale` replaced `preferred_language`, default `mr`.
`gst_last4` is four digits, not a GSTIN. `on_time_payment_bps` / `renegotiation_bps`
are integer bps, not floats. `voice.py` is an empty router — exactly right, I7 holds.
`app/routers/meta.py` `/health` returns `db` / `model_loaded` / `latest_obs_date`.
`price_engine` now stamps `source: "SYNTHETIC"` on every row, so **I8 is satisfiable
on the wire** and our badge has something to read.

That is a real pass. B1 and B3 alone were the difference between "the farmer app is
unreachable" and "onboarding works".

---

## 2. Field-level mismatches — mechanical, cheap, mine or his

### 2.1 `WindowRes` — seven renames/retypes (`app/schemas/ai.py`)

| His | Ours | Who should move |
|---|---|---|
| `recommendation` | **`action`** | **His.** Ours is read as `action` by S9, S10, S11 and the fixture set. |
| `itemised_costs` | **`costs`** | **His**, same reason. |
| `pledge_quote: Optional[int]` | `PledgeQuote \| null` — an **object** of 7 fields | His |
| `alt_market: Optional[str]` | `AltMarket \| null` — an **object** of 4 fields | His |
| `explain_mr` / `explain_en`: `Optional[str]` | **non-nullable `string`** | His — see 3.3, this is I16-adjacent |
| `ModelCard {mase, coverage_80_bps}` | `ModelCardSummary` — same two fields | ✅ already matches |
| `hold_p50/p10_net…`, `expected_gain_paise`, `worst_case_paise`: `int` | all `number \| null` | Either. `int` is a strict subset; safe until a refusal needs to null them. |

Already correct and worth saying so: the five-value `recommendation` Literal, all
**six** per-quintal cost keys, `confidence` as `LOW|MEDIUM|HIGH`, `band_width_bps` as
an int, and the **correct four** `refusal_reason` values including `GAIN_BELOW_COST`.
`WindowReq` matches ours field-for-field including `qty_kg` and `lot_id: Optional`.

### 2.2 `id: int` was fixed in exactly one place

`UserResponse.id` is now `str`. Every other id on the wire is still an integer:

- `app/schemas/ref.py` — `DistrictOut.id`, `CommodityOut.id`, `WarehouseOut.id`, `MandiOut.id`, `district_id` → all `int`
- `app/schemas/lot.py` — `LotOut.id`, `commodity_id`, `market_id`, `warehouse_id`, `SelfAssayResponse.lot_id` → all `int`
- `app/schemas/auth.py` — `district_id: Optional[int]` (no coercing validator, unlike `id`)
- path params — `lots/{lot_id}` is typed `lot_id: int`

Ours are `string` everywhere. This is the bug that compiles clean and breaks at the
first template-literal cache key. It also means our fixture ids (`lot_listed_1`,
`cmd_onion`) will 422 against his path/query validators. **One `str` + one
`field_validator` per schema; `MandiOut.lat/lng` also needs `lng` → `lon` to match ours.**

### 2.3 `/lots` — the 100× hazard, again

`app/schemas/lot.py` uses **`quantity_qtl`**. Ours is **`qty_kg`** (I2: store kg,
display quintals). A silent unit swap on a create path is exactly the class of error
that puts a 100× number on screen. `LotOut` is also missing `farmer_id`,
`harvest_date`, `created_at`, and calls the photo `image_url` where ours is
`photo_path`. `LotOut.grade`/`status` are unconstrained `str` — ours are closed
unions of four and six values, and `UNGRADED` must survive as its own value rather
than arriving as `null`.

### 2.4 `/auth/me` shape

He returns `UserDetailResponse` **flat**. Our client is
`getMe = () => get<{ user: User }>('/auth/me')` — wrapped. One of the two wraps;
his `AuthResponse` already wraps as `{user, token}`, so wrapping `/auth/me` is
consistent with his own file.

### 2.5 `/meta/init` will 500 on every call

`app/routers/meta.py` — `AppInitRes` declares `commodities` as **required**,
`comm_out` is computed, and then `return AppInitRes(roles=roles, markets=mandis_out)`
omits it. Pydantic raises. We do not call this route, so it costs us nothing, but it
is a one-word fix and it will look bad in a live demo.

### 2.6 `/meta/data-provenance` is a different object

He returns `{"sources": [...], "last_sync": "..."}`. Ours is
`{rows: ProvenanceRow[], generated_at}` — per-(commodity, market) row counts with
`first_obs_date`, `last_obs_date`, `source`, `source_url`. S24 renders the table;
a flat list of source names gives it nothing to draw. Low priority: S24 is on
fixtures and stays there.

### 2.7 `random`, not `secrets` (I15)

`app/services/auth_service.py:18` — `code = f"{random.randint(0, 999999):06d}"`.
The hashing and TTL around it are right; the generator is not. `secrets.randbelow`,
one line.

---

## 3. The hero endpoint — the part that actually matters

`POST /api/v1/ai/window/recommend` now exists, is reachable, calls
`compute_sale_window`, and the `@cache(expire=3600)` is gone. Four problems, in
descending order of consequence.

### 3.1 It returns `SELL_NOW` with all zeros, for every input

This is arithmetic from his own constants, not a hunch. `app/engines/window_engine.py`:

- `sell_now_net = current_price_mid_paise` — **no costs subtracted**, and the comment says so ("ignoring baseline transport for simplicity")
- every hold day subtracts commission (2.5 % ≈ ₹52/qtl), loading (₹20/qtl), storage, spoilage and transport

So the hold branch is charged for commission and loading that apply *either way*,
and `sell_now` is not. On onion at ₹2,100/qtl, day 1 costs ≈ ₹82/qtl against a
0.3 %/day drift of ≈ ₹6/qtl. `gain` is negative on day 1 and stays negative through
day 14. `best_gain` never exceeds 0 → the `best_day is None or best_gain <= 0`
branch always fires → the response is:

```
recommendation: "SELL_NOW", confidence: "HIGH", band_width_bps: 2000,
expected_gain_paise: 0, worst_case_paise: 0,
itemised_costs: {all six keys: 0},
explain_mr: null, explain_en: null, hold_days: null
```

S9 renders "₹0 expected, ₹0 worst case", S10's cost breakdown is six zeroes, and
there is no Marathi sentence. He was told this on the old `SELL` branch and it
survived the rewrite. **Fix: subtract the always-applicable costs from `sell_now_net`
too, and populate `itemised_costs` with today's real numbers on the SELL_NOW branch.**

### 3.2 `NO_ADVICE` is unreachable — I6 cannot be demonstrated

`price_engine.predict` hardcodes `p10 = 0.90 × p50`, `p90 = 1.10 × p50`. So
`band_width_bps = (p90 − p10) / p50 × 10000` is **always exactly 2000**.
`predict_range` scales all three quantiles by the same trend, so the ratio never
moves. The refusal threshold is 2500. The band can never cross it.

`confidence` is likewise pinned: `0.85` fixed → always `"HIGH"`.

`docs/architecture/00_CANON.md` I6 and `CLAUDE.md` §2 both call I6 one of the two a
judge will actually test — *"they will ask what happens when the model is wrong"*.
Right now the answer is that it structurally cannot say it does not know. **The
quantile spread has to vary with the data, or the demo lot has to be seeded so that
one commodity/market pair genuinely produces a wide band.**

### 3.3 No `explain_mr` on the success paths

`window_engine` sets `explain_mr` / `explain_en` **only** inside the
`NO_ADVICE` branch. `SELL_NOW` and `HOLD` return `null` for both. Ours types them
non-nullable and renders them verbatim — we do not translate client-side, by design.
A farmer-facing recommendation with no Marathi sentence is not shippable, and per
`CLAUDE.md` §8.6 Marathi strings must exist for anything a farmer sees.

### 3.4 Three smaller things in `app/routers/ai.py`

- `price_engine.predict(payload.market_id, payload.commodity_id, "")` — the signature is `predict(self, mandi, commodity, date)`. **Market and commodity are swapped.** The result: `base_prices.get(market_id.lower(), 200000)` never matches a crop name, so *every* lot silently falls back to ₹2,000/qtl, and the mandi factor is computed from the commodity string. Both inputs are being read as the other.
- `distance_km = 50.0`, hardcoded, comment "Assume distance is 50km for stub". Combined with `transport = 50 paise/km × 50 km ÷ 40 qtl` that is **₹0.62 per quintal** of transport. Real is two orders of magnitude higher. S10 shows this number to a judge.
- `except Exception: current_mid = 200000` — a model failure produces a confident fabricated price instead of `NO_ADVICE` / `INSUFFICIENT_HISTORY`. Same hazard as the `except Exception: pass` still wrapped around `load_models()` in `main.py`.

### 3.5 Two of five actions are unreachable

`SELL_ELSEWHERE` and `SPLIT` are in the Literal but nothing in `window_engine`
emits them, and `alt_market` is hardcoded `None`. Fine for now — S9 handles all five
and our fixtures cover the missing two — but the enum currently overstates the engine.

---

## 4. Prices and reference — closest to done

`app/routers/prices.py` `/series` is genuinely good: `PricePoint` matches ours
field-for-field, `source` is whitelisted against our five `DataSource` values with an
`IMPUTED` fallback, `source_summary` counts by source, `latest_obs_date` is real.
That unblocks S5's provenance badge cleanly.

`/nearby` has the right shape — all six per-quintal keys, `market_id` stringified,
sorted by `net_paise_per_qtl` descending, which is the product — but every number is
a hardcoded mock (`gross = 250000`, `transport = 15000`, `distance_km = 45` for every
market). S6's whole point is that a nearer mandi paying less gross can outrank a
distant one; with constant inputs the ordering carries no information.

`app/routers/ref.py` has all four lists we asked for. Only the `int` ids and
`lng`→`lon` stand between it and drop-in usable.

---

## 5. What I need from him next, in order

1. **`recommendation` → `action`, `itemised_costs` → `costs`.** Two renames, unblocks a mechanical diff of everything else.
2. **Fix the swapped args** in `ai.py` — `predict(mandi=market_id, commodity=commodity_id)`. One line, and until it lands every price in the system is the ₹2,000 fallback.
3. **Subtract always-applicable costs from `sell_now_net`, and return real `itemised_costs` on the SELL_NOW branch.** Without this the hero is ₹0/₹0 forever.
4. **`explain_mr` + `explain_en` on every branch**, not just refusals.
5. **Make the band vary** so `NO_ADVICE` is reachable, or tell me which seeded (commodity, market) pair will trigger it so I can point the demo at it.
6. **`str` ids everywhere** — `ref.py`, `lot.py`, `district_id`, and the `{lot_id}` path params. Plus `lng` → `lon`.
7. **`quantity_qtl` → `qty_kg`** on `LotCreate`/`LotOut`, and add `farmer_id`, `harvest_date`, `created_at`; rename `image_url` → `photo_path`.
8. **`pledge_quote` and `alt_market` as objects**, or explicitly `null` forever and I keep them on fixtures.
9. **`secrets` instead of `random`** for the OTP.
10. **`openapi.json`.** Still the single artifact that ends all of this. `curl localhost:8000/openapi.json` once the API boots, commit it, and I diff mechanically instead of reading files by hand.

Items 1–5 are the hero. If he only does those five, the demo has a real
recommendation. 6–9 are merge-day work. 10 makes every future round of this cheap.

**Explicitly not asking for:** offers, counter-offers, escrow FSM, disputes, buyer
reliability, the realisation ledger, pools. Those stay on our fixtures permanently
and the screens are built to be indistinguishable from live. `voice.py` stays empty.

---

## 6. Where that leaves us

Nothing in this document changes what I build this week. Fixtures are the plan until
merge, `USE_FIXTURES` and `FIXTURE_LOTS_EMPTY` are the switches, and the frontend
contract in `app/src/types/api.ts` is the thing both sides converge on.

The honest summary for a status update: **the wire contract is about three-quarters
aligned and the remaining quarter is mechanical renames. The numbers behind it are
not yet real, and the refusal path — the one thing we tell judges is the product —
cannot currently fire.** Those are two different problems and only the second one is
hard.




Akash — I read your repo at commit efea078 against our frontend contract
(app/src/types/api.ts). Everything below cites your own files.

First, the honest scorecard: every SHAPE thing I asked for last round landed,
and landed carefully. B1 role casing, B2 id:str, B3 the whole OTP flow, B4 both
handlers (not just the middleware), B5 the /api/v1 prefix. schemas/ai.py is
near-perfect: five-value action enum, all six per-quintal cost keys, all four
refusal reasons including GAIN_BELOW_COST, confidence as LOW|MEDIUM|HIGH,
band_width_bps as an int. You killed the @cache(expire=3600) and the
hash(mandi) PYTHONHASHSEED bug without being asked twice. Leaving voice.py
empty was correct. price_engine now stamps source:"SYNTHETIC" on every row,
which is the one thing that cannot be walked back, so thank you.

Every NUMBER thing I asked for did not land. Item 3 below is verbatim from my
last message and survived a full rewrite. I'm assuming it read as a
nice-to-have. It isn't — it's the only thing between the hero endpoint and
being useless, and it's about four lines.

Five things, in order. All five are in the hero. Nothing else on this list
matters until these are done.

---

1. SWAPPED ARGUMENTS — one line, do this first.

app/routers/ai.py calls:
    price_engine.predict(payload.market_id, payload.commodity_id, "")
The signature in price_engine.py is:
    predict(self, mandi: str, commodity: str, date: str)

Market and commodity are reversed. So base_prices.get(commodity.lower(),
200000) is being handed a market_id, never matches a crop name, and returns
the 200000 fallback. Meanwhile mandi_factor is computed from the commodity
string. Right now EVERY lot in the system returns the flat Rs 2,000/qtl
fallback price. Fix:
    price_engine.predict(payload.commodity_id, ... )  # match the signature order

While you're in that file: `except Exception: current_mid = 200000` invents a
confident fabricated price on model failure. That must return NO_ADVICE with
refusal_reason INSUFFICIENT_HISTORY instead. A wrong number is worse than no
number — that is the entire product thesis.

Also `distance_km = 50.0` hardcoded, with transport = 50 paise/km * 50km / 40
qtl = Rs 0.62 per quintal of transport cost. Real is two orders of magnitude
higher. Our cost-breakdown screen shows that number to a judge.

---

2. THE HERO RETURNS ALL ZEROS FOR EVERY INPUT.

app/engines/window_engine.py:
    sell_now_net = current_price_mid_paise
    # comment: "ignoring baseline transport for simplicity"

sell_now has NO costs subtracted. Every hold day is charged commission
(2.5%), loading (Rs 20/qtl), storage, spoilage and transport. Commission and
loading apply whether the farmer sells today or in nine days — charging them
to only one branch makes holding structurally unprofitable.

I ran your own constants on onion at Rs 2,100/qtl:
    day 1  : costs 8062 paise/qtl vs 0.3%/day drift of ~600 paise → gain -4062
    day 7  : costs 13552 → gain -5952
    day 14 : costs 19957 → gain -8157

Negative on all 14 days, even with best-case trend noise. So best_gain <= 0
always fires, and the response is ALWAYS:
    recommendation "SELL_NOW", confidence "HIGH", band_width_bps 2000,
    expected_gain_paise 0, worst_case_paise 0,
    itemised_costs {all six keys: 0}, explain_mr null, hold_days null

Our verdict screen renders "Rs 0 expected, Rs 0 worst case" and our cost
breakdown renders six zeroes.

Fix, two parts:
  (a) Subtract the always-applicable costs (commission + loading + baseline
      transport) from sell_now_net too, so the comparison is like-for-like.
  (b) Populate itemised_costs with today's real computed numbers on the
      SELL_NOW branch, not zeros.

---

3. NO_ADVICE IS MATHEMATICALLY UNREACHABLE — this is the invariant judges test.

app/engines/price_engine.py:
    p50 = base
    p10 = int(p50 * 0.90)
    p90 = int(p50 * 1.10)

The ratios are hardcoded, so:
    band_width_bps = (p90 - p10) / p50 * 10000 = ALWAYS EXACTLY 2000

Your BAND_WIDTH_THRESHOLD is 0.25 (2500 bps). 2000 < 2500, forever. The band
cannot cross the threshold under any input. predict_range scales all three
quantiles by the same trend factor, so the ratio never moves there either.

confidence is likewise pinned: 0.85 fixed → always "HIGH".

Our whole pitch is that the model refuses when it doesn't know. Right now it
structurally cannot say that. Either:
  (a) make the quantile spread vary with the data (wider for volatile
      commodities, wider at longer horizons, wider with sparse history), or
  (b) tell me exactly which seeded (commodity, market) pair produces a band
      above 2500 bps, and I point the demo at that lot.

Either answer works. Silence does not.

ALSO — we disagree on the threshold itself. Our config says 3500 bps (35%),
citing 05_AI_ARCHITECTURE.md section 6 and NILESH.md section 2. Yours is 2500
bps (25%). Our refusal screen prints the limit on screen, so right now it
would display a number your server never applies. Tell me which is correct
and I'll match it. I don't care which, I care that it's one number.

---

4. explain_mr AND explain_en ON EVERY BRANCH, NOT JUST REFUSALS.

window_engine sets both only inside the NO_ADVICE branch. SELL_NOW and HOLD
return null for both. Our types declare them non-nullable and we render them
verbatim — we do not translate client-side, by design. A farmer-facing
recommendation with no Marathi sentence is not shippable.

---

5. TWO RENAMES.

    recommendation  →  action
    itemised_costs  →  costs

Ours is read as `action` by three screens and the whole fixture set. Two lines
on your side, six files on mine.

---

MERGE-DAY, NOT NOW — do not spend hero hours on these:

- str ids everywhere. You fixed UserResponse.id only. Still int:
  ref.py (DistrictOut.id, CommodityOut.id, WarehouseOut.id, MandiOut.id,
  district_id), lot.py (LotOut.id, commodity_id, market_id, warehouse_id,
  SelfAssayResponse.lot_id), auth.py district_id, and the {lot_id} path
  params. One str + one field_validator per schema. Our fixture ids are
  "lot_listed_1" and "cmd_onion" — they will 422 against your int validators.

- MandiOut.lng → lon. Ours is lon.

- LotCreate/LotOut quantity_qtl → qty_kg. This is a unit swap on a create
  path — the 100x class of error, the kind that puts a wrong number on screen
  in front of a judge. We store kg and display quintals. Also LotOut is
  missing farmer_id, harvest_date, created_at, and calls the photo image_url
  where ours is photo_path. LotOut.grade and .status are unconstrained str;
  ours are closed unions, and UNGRADED must arrive as its own value, never
  as null.

- /auth/me returns UserDetailResponse flat. Our client expects {user: {...}}.
  Your own AuthResponse already wraps as {user, token}, so wrapping /me is
  consistent with your own file.

- OTP uses random.randint. Use secrets. One line, and it's a security
  invariant we wrote down.

- /meta/init 500s on every call. AppInitRes declares commodities as required,
  you compute comm_out, then return AppInitRes(roles=roles,
  markets=mandis_out) and omit it. Pydantic raises. We don't call the route,
  but it will look bad live.

- except Exception: pass around load_models() in main.py. A failed model load
  boots the API "healthy" with no model.

---

WHAT'S ALREADY GOOD, so you don't touch it:

prices.py /series is the best file in your repo. PricePoint matches ours
field-for-field, source is whitelisted against our five DataSource values with
an IMPUTED fallback, source_summary and latest_obs_date are real. That
unblocks our provenance badge cleanly. Don't change it.

/nearby has exactly the right shape — all six per-quintal keys, market_id
stringified, sorted by net_paise_per_qtl descending. But every number is a
hardcoded mock (gross 250000, transport 15000, distance_km 45 for every
market). The entire point of that screen is that a nearer mandi paying less
gross can beat a distant one paying more — with constant inputs the ordering
carries zero information. Lower priority than the hero, but it's a demo beat.

ref.py has all four lists we need. Only the int ids and lng→lon stand between
it and drop-in usable.

---

NOT ASKING FOR, EVER — stop if you started any of these:

offers, counter-offers, escrow FSM, disputes, buyer reliability, the
realisation ledger, pools. All of it stays on our fixtures permanently and
those screens are built to be indistinguishable from live. voice.py stays
empty. Ignore the rest of the handover doc.

---

ONE ARTIFACT ENDS ALL OF THIS:

Boot the API and run:
    curl localhost:8000/openapi.json > openapi.json
Commit it. Then I diff your contract against our client mechanically in thirty
seconds instead of reading eleven of your files by hand. This is the highest
leverage thing you can do for me after items 1-5 and it takes one minute.

Items 1-5 are the hero. If you do only those five, the demo has a real
recommendation. Everything else can wait for merge day.