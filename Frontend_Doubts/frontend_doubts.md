Akash — I read Neolithic-Backend at 9137d75. Everything below cites your own files so we're arguing about code, not summaries. Ranked by what breaks the demo silently.

Blocking — these five, in this order

B1. role is lowercase → every farmer gets the buyer console.
app/schemas/auth.py → role: str = Field(..., pattern=r"^(farmer|buyer|fpo_admin)$"). Our root navigator branches on user.role === 'FARMER'. Lowercase means that's false for everyone and the whole farmer app is unreachable — silently, no error. Send FARMER / BUYER uppercase. Also: we have no branch for fpo_admin; if it must exist, it needs to arrive as FARMER for now.

B2. id: int → send id: str.
UserResponse.id: int, fpo_id: Optional[int]. We type every id as string. JSON 1 vs "f1" compiles clean in TypeScript and then breaks at the first template-literal key or ===. This is the one bug neither of us will see until it's live. Same for lot ids, offer ids, market ids — all ids stringly-typed on the wire.

B3. Auth is phone + password. We have no password field and won't add one.
app/routers/auth.py has only POST /auth/register and POST /auth/login ("Login with phone and password"), with password: str = Field(..., min_length=6). Our entire onboarding is OTP: POST /auth/otp/request {phone} → POST /auth/otp/verify {phone, code} → POST /auth/register. Two screens (S2, S3) are built against that and a farmer-facing password is the wrong design for this user. Also, as written, register returns a JWT with verified: false — a token with no proof of phone ownership at all. We need the two OTP routes; store code_hash, never plaintext, and generate from secrets, not random.

B4. Error envelope. app/middleware/error_handler.py returns {"detail": "Internal server error"}. FastAPI's HTTPException bypasses that middleware entirely and Pydantic 422 returns detail as an array. So your API emits three different error shapes and our client parses none of them — every screen's error state degrades to a generic fallback. One envelope, every failure, no exceptions:

{"error": {"code": "LOT_NOT_FOUND", "message": "…", "field": null}}

Add an HTTPException handler and a RequestValidationError handler, not just the middleware.

B5. No /api/v1 prefix. main.py mounts at bare /auth, /users, /lots… One APIRouter(prefix="/api/v1") parent, or one kwarg per include_router. You already flagged this; it's cheap and it's in front of everything else.

The hero — four mismatches at once

app/routers/ai.py is a stub: GET /ai/sale-window → return {}, GET /ai/price-forecast → return [], both under # TODO: Nikhil implements these endpoints. So the engine in window_engine.py is not reachable over HTTP at all. When you wire it:

	We call	You have
Path	POST /api/v1/ai/window/recommend	GET /ai/sale-window
Input	JSON body	?lot_id= query param
Common case	lot_id: null	lot_id required
Response	full WindowRes	{}

The lot_id: null case is not an edge case — it's the main one. S9 is reachable from the home screen before a farmer has ever created a lot. compute_sale_window() needs quantity_kg and distance_km, which you're deriving from a lot that doesn't exist yet. Take them from the body instead:

{"commodity_id": "…", "market_id": "…", "qty_kg": 4000,
 "grade": "A", "lot_id": null, "horizon_days": 14}

Verdict enum. You return "SELL" / "HOLD" / "NO_ADVICE". We render five: SELL_NOW, SELL_ELSEWHERE, HOLD, SPLIT, NO_ADVICE. SELL ≠ SELL_NOW, and SELL_ELSEWHERE / SPLIT don't exist in your engine.

Refusal. You return reason as an English f-string: f"Forecast too uncertain for {crop} at {mandi} (band width {band_width:.0%}…)". We need refusal_reason as an enum — BAND_TOO_WIDE | INSUFFICIENT_HISTORY | STALE_DATA | GAIN_BELOW_COST — because the Marathi sentence is chosen from it. A farmer cannot read that f-string. Every response also needs explain_mr and explain_en, rendered verbatim; we don't translate client-side.

Costs — this is where a 100× error hides. Yours are whole-lot with four keys: transport_paise, commission_paise, storage_paise, spoilage_estimate_paise. Ours are per quintal with six: transport_paise_per_qtl, commission_paise_per_qtl, storage_paise_per_qtl, spoilage_paise_per_qtl, loading_paise_per_qtl, total_paise_per_qtl. Note _per_qtl on every one, and that expected_gain_paise / worst_case_paise are the opposite — whole lot. The two identities must hold exactly:

expected_gain_paise = (hold_p50_net − sell_now_net) × (qty_kg // 100)
worst_case_paise    = (hold_p10_net − sell_now_net) × (qty_kg // 100)

On our reference 40-quintal lot that closes at ₹6,290 / −₹4,800. If yours closes at ₹62,900, a unit is wrong.

Also missing from the response and needed by the screen: confidence as 'LOW'|'MEDIUM'|'HIGH' (you compute a float and then discard it), band_width_bps as an integer bps (you compute a float ratio and discard it), sell_now_net_paise_per_qtl, hold_p50_net_paise_per_qtl, hold_p10_net_paise_per_qtl, model_card: {mase, coverage_80_bps}, data_source, pledge_quote (or null), alt_market (or null). Every key always present — the nullable ones go null on a refusal, they don't vanish.

On the SELL branch you return zeros: expected_gain_paise: 0, worst_case_paise: 0, itemised_costs: {}. That renders as "₹0 gain, ₹0 worst case" and leaves our cost-breakdown screen with nothing. Return the real computed values for today.

Two problems in your code that aren't on your list

@cache(expire=3600) on the hero. An hour-stale "act today or wait nine days" number is wrong by construction. Worse, the cache key doesn't include the actor — a shared cache on a route that reads user-owned data is the exact hazard behind our rule that every read is scoped by the JWT, never by a client-supplied id, and returns 404 not 403 on a miss. Drop the cache on /ai/* recommend, or key it by actor + inputs.

except Exception: pass around price_engine.load_models() in main.py. A failed model load is completely silent — the API boots "healthy" with no model. That's a legitimate state, but it must return 200 with NO_ADVICE / INSUFFICIENT_HISTORY, never a 500 and never a fabricated number. Also hash(mandi) in price_engine is randomised per process by PYTHONHASHSEED, so the same mandi produces different base prices after every restart.

The forecast is currently synthetic and unlabelled — this is the one that can't be recovered

price_engine.py says it plainly: "This is a stub implementation using mock data." It uses random.uniform() for both confidence and the daily trend, over a hardcoded base_prices dict keyed on lowercase English crop names (wheat, rice, onion, potato, tomato, soybean) — with a silent fallback to 200000 for anything unknown, so a bad commodity returns a confident fabricated price instead of a 404.

Until real model artifacts land, every row you return must carry source and source_url, and synthetic rows must be source: "SYNTHETIC". Our UI badges anything that isn't AGMARKNET or MSAMB, and it can only do that if the field is there. Showing unlabelled synthetic numbers to a government panel is the one mistake we cannot walk back. Allowed values: AGMARKNET | MSAMB | ARCHIVE | IMPUTED | SYNTHETIC.

Path renames + what's absent entirely

Rename: /transactions → /tx · /fpo → /pools · /ai/price-forecast → /ai/forecast (with commodity_id, market_id, horizon — you have ?mandi=&commodity= and no horizon) · /mandi-locations + /logistics → under /ref/*.

Absent, and each one has a screen waiting: /ref/districts (S3's picker has no list, and your user object has lat/lng but no district_id — we key three screens off it) · /ref/markets · /prices/series · /prices/nearby · /ai/model-card (full card for S8) · /meta/health · /meta/data-provenance (S24 has nothing to render) · /grade. Your /health returns only {"status":"ok"} — we need db, model_loaded, latest_obs_date.

Minor: preferred_language should be locale, values 'mr'|'hi'|'en', default mr not en.

Don't build these

app/routers/voice.py plans POST /voice/narrate via Bhashini and Agora/ZegoCloud calls. Our demo makes zero live external network calls — venue wifi fails, it always fails. Voice is pre-generated Marathi mp3 played offline; calls are a tel: intent. Please leave that router empty and spend the hours on B1–B5.

What we are not asking you for

Everything from offers onward — counter-offers, escrow FSM, disputes, buyer reliability, the realisation ledger — stays on our fixtures, permanently, and those screens are built to be indistinguishable from live. Ignore the rest of the handover doc. If you only ship B1–B5 plus the /prices and /ref routes, we can merge. Nothing below that line is worth your remaining hours.

One artifact ends all of this guessing

Run the API and send me openapi.json (curl localhost:8000/openapi.json). Then I diff it against our client mechanically instead of us trading summaries. Three of the things above contradict what you told me earlier — not your fault, the summary and the source have drifted.

Still unanswered from my earlier list and blocking us: Q1, Q2, Q6, Q8.