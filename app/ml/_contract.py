"""
Frozen data-shape contract — Phase 0 lock.

These TypedDicts define the EXACT fields and types for the two core
response shapes.  Person B mirrors them as Pydantic models in
``app/schemas/ai.py`` (Phase 2B/5).  Person A uses them for test fixtures.

Do NOT add, remove, or rename fields without both-person agreement.
"""

from __future__ import annotations

from typing import TypedDict


# ── CostBreakdown (used inside WindowRes) ──────────────────────────────
class CostBreakdown(TypedDict):
    """All values in integer paise.  5 lines == total exactly."""
    transport_paise: int
    commission_paise: int
    loading_paise: int
    storage_paise: int
    spoilage_paise: int
    total_paise: int


# ── WindowRes ──────────────────────────────────────────────────────────
class WindowRes(TypedDict):
    """Response from the hold/sell decision engine.

    action: SELL_NOW | HOLD | SPLIT | SELL_ELSEWHERE | NO_ADVICE
    hold_days: 0 if SELL_NOW; 1..14 for HOLD/SPLIT
    confidence: low | medium | high
    expected_gain_paise: net gain after all costs (0 for SELL_NOW)
    worst_case_paise: p10 scenario net (0 for SELL_NOW)
    refusal_reason: str | None — set only when action == NO_ADVICE
        One of: BAND_TOO_WIDE, INSUFFICIENT_HISTORY, STALE_DATA,
        GAIN_BELOW_COST, MODEL_UNAVAILABLE
    band_width_bps: (p90 − p10) / p50 × 10000 at chosen hold day
    sell_now_net_paise_per_qtl: net if selling today after costs
    costs: CostBreakdown
    explain_mr: str — Marathi one-liner for the voice layer
    explain_en: str — English one-liner (debug / model-card)
    """
    action: str               # enum: SELL_NOW | HOLD | SPLIT | SELL_ELSEWHERE | NO_ADVICE
    hold_days: int             # 0..14
    confidence: str            # enum: low | medium | high
    expected_gain_paise: int   # net after all costs
    worst_case_paise: int      # p10 scenario net
    refusal_reason: str | None
    band_width_bps: int        # basis points
    sell_now_net_paise_per_qtl: int
    costs: CostBreakdown
    explain_mr: str
    explain_en: str


# ── ForecastDay ────────────────────────────────────────────────────────
class ForecastDay(TypedDict):
    """One day of the 14-day forecast, returned by /ai/price-forecast."""
    date: str          # YYYY-MM-DD
    p10_paise: int
    p50_paise: int
    p90_paise: int


# ── PledgeQuote ────────────────────────────────────────────────────────
class PledgeQuote(TypedDict):
    """Pledge card — only present when HOLD + gain > interest.

    loan_paise: amount the farmer receives today
    interest_paise: total interest over hold_days
    net_benefit_paise: expected_gain − interest
    assessed_value_paise: crop value (p10-conservative, grade-adjusted)
    days: same as WindowRes.hold_days
    ltv_bps: loan-to-value in basis points (e.g. 7000 = 70%)
    rate_bps_annual: annual interest rate in bps (e.g. 1200 = 12%)
    warehouse_id: which warehouse stores the crop
    is_wdra_registered: bool — WDRA registration status
    disclaimer: fixed legal disclaimer string
    """
    loan_paise: int
    interest_paise: int
    net_benefit_paise: int
    assessed_value_paise: int
    days: int
    ltv_bps: int
    rate_bps_annual: int
    warehouse_id: int | None
    is_wdra_registered: bool
    disclaimer: str


# ── ModelCard ──────────────────────────────────────────────────────────
class ModelCard(TypedDict):
    """Provenance and quality metadata for a trained model."""
    commodity: str
    pooled_mandis: list[str]
    training_rows: int
    feature_count: int
    mase_pooled: float
    mase_per_mandi: dict[str, float]       # mandi -> MASE
    coverage_bps_pooled: int               # empirical p10-p90 coverage (basis points)
    coverage_bps_per_mandi: dict[str, int]
    horizon_days: int
    quantile_alphas: list[float]
    trained_at: str                        # ISO datetime
    data_source: str                       # "real" | "imputed" | "mixed"
    known_limitations: list[str]


# ── ReplayPoint ────────────────────────────────────────────────────────
class ReplayPoint(TypedDict):
    """One spotlight date for the predicted-vs-actual demo."""
    cutoff_date: str                       # "pretend today"
    commodity: str
    market: str
    forecast: list[ForecastDay]            # 14-day forecast made on cutoff_date
    actual_paise: list[int]                # what actually happened (14 values)
    band_contained_actual: list[bool]      # per-day: actual ∈ [p10, p90]?
    mase_at_cutoff: float
    coverage_at_cutoff_bps: int
