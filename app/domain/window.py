"""Hold/sell decision engine — the core logic that turns a forecast into
a recommendation.  Pure functions, no DB or HTTP.

Unit convention (IMPORTANT — matches the frontend contract):
  * All prices are per quintal (paise/quintal).
  * ``sell_now_net_paise_per_qtl``, ``hold_p50_net_paise_per_qtl``,
    ``hold_p10_net_paise_per_qtl`` are PER QUINTAL.
  * ``expected_gain_paise`` and ``worst_case_paise`` are WHOLE LOT
    (= per-qtl difference × qty_qtl), per the frontend identities:
      expected_gain_paise = (hold_p50_net − sell_now_net) × qty_qtl
      worst_case_paise    = (hold_p10_net − sell_now_net) × qty_qtl
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from app.domain.constants import (
    FORECAST_HORIZON_DAYS,
    MIN_GAIN_PAISE,
    MIN_HISTORY_ROWS,
    NO_ADVICE_BAND_BPS,
)
from app.domain.costs import CostBreakdown, compute_costs
from app.ml.quantile import ModelUnavailable, predict_quantiles


# ── Refusal reasons ────────────────────────────────────────────────────
BAND_TOO_WIDE = "BAND_TOO_WIDE"
INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"
STALE_DATA = "STALE_DATA"
GAIN_BELOW_COST = "GAIN_BELOW_COST"
MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"


@dataclass(frozen=True, slots=True)
class WindowResult:
    """Decision output — mirrors the WindowRes TypedDict / Pydantic model."""
    action: str                       # SELL_NOW | HOLD | SPLIT | SELL_ELSEWHERE | NO_ADVICE
    hold_days: int                    # 0 for SELL_NOW, 1..14 for HOLD/SPLIT
    confidence: str                   # low | medium | high
    expected_gain_paise: int          # WHOLE LOT net gain (per-qtl × qty_qtl)
    worst_case_paise: int             # WHOLE LOT p10-scenario net
    refusal_reason: str | None        # set only when action == NO_ADVICE
    band_width_bps: int               # (p90 − p10) / p50 × 10000 at chosen day
    sell_now_net_paise_per_qtl: int   # per-quintal net if selling today
    hold_p50_net_paise_per_qtl: int   # per-quintal net at best hold day (p50)
    hold_p10_net_paise_per_qtl: int   # per-quintal net at best hold day (p10)
    costs: CostBreakdown              # WHOLE LOT costs at chosen hold day
    explain_mr: str                   # Marathi one-liner
    explain_en: str                   # English one-liner


def _no_advice(reason: str, explain_mr: str, explain_en: str) -> WindowResult:
    return WindowResult(
        action="NO_ADVICE", hold_days=0, confidence="low",
        expected_gain_paise=0, worst_case_paise=0,
        refusal_reason=reason, band_width_bps=0,
        sell_now_net_paise_per_qtl=0,
        hold_p50_net_paise_per_qtl=0,
        hold_p10_net_paise_per_qtl=0,
        costs=CostBreakdown(0, 0, 0, 0, 0, 0),
        explain_mr=explain_mr, explain_en=explain_en,
    )


def _band_width_bps(p10: int, p50: int, p90: int) -> int:
    """(p90 − p10) / p50 × 10000.  Guard against p50 == 0."""
    if p50 <= 0:
        return 10_000  # treat as 100% uncertainty
    return (p90 - p10) * 10_000 // p50


def decide(
    commodity: str,
    market: str,
    spot_price_paise_per_qtl: int,
    quantity_kg: int,
    distance_km: float,
    history_rows: int,
    as_of: str | date | datetime,
) -> WindowResult:
    """Produce a hold/sell/no-advice recommendation.

    Parameters
    ----------
    commodity            : str   e.g. "Onion"
    market               : str   e.g. "Lasalgaon APMC"
    spot_price_paise_per_qtl : int  Current modal price, paise per QUINTAL
    quantity_kg          : int   Lot weight in kg
    distance_km          : float Nearest good-market distance
    history_rows         : int   How many days of history we have for this series
    as_of                : date  "Today" (or walk-forward cutoff)

    Returns
    -------
    WindowResult — never raises; refusal → NO_ADVICE with reason.
    """
    qty_qtl = max(1, quantity_kg // 100)

    # ── Refusal gate 1: insufficient history ───────────────────────────
    if history_rows < MIN_HISTORY_ROWS:
        return _no_advice(
            INSUFFICIENT_HISTORY,
            f"कमीत कमी {MIN_HISTORY_ROWS} दिवसांचा इतिहास लागतो",
            f"Need at least {MIN_HISTORY_ROWS} days of history",
        )

    # ── Refusal gate 2: model unavailable ──────────────────────────────
    try:
        quantiles = predict_quantiles(commodity, market, as_of, FORECAST_HORIZON_DAYS)
    except ModelUnavailable:
        return _no_advice(
            MODEL_UNAVAILABLE,
            f"{commodity} साठी मॉडेल उपलब्ध नाही",
            f"Model not available for {commodity}",
        )

    # ── Refusal gate 3: spot price non-positive ────────────────────────
    if spot_price_paise_per_qtl <= 0:
        return _no_advice(
            STALE_DATA,
            "चालू भाव उपलब्ध नाही",
            "Current spot price unavailable",
        )

    # ── Sell-now baseline (per quintal) ────────────────────────────────
    sell_now_costs = compute_costs(spot_price_paise_per_qtl, quantity_kg, distance_km, days=0)
    sell_now_net_qtl = spot_price_paise_per_qtl - sell_now_costs.total_paise // qty_qtl

    # ── Evaluate each hold day (per quintal) ───────────────────────────
    best_day = 0
    best_gain_qtl = 0          # gain vs sell-now, per quintal
    best_worst_qtl = 0         # p10 scenario vs sell-now, per quintal
    best_costs = sell_now_costs
    best_p50_net_qtl = sell_now_net_qtl
    best_p10_net_qtl = sell_now_net_qtl

    for h in range(1, FORECAST_HORIZON_DAYS + 1):
        p10, p50, p90 = quantiles[h - 1]
        costs = compute_costs(p50, quantity_kg, distance_km, days=h)

        # Net per quintal if we sell at p50 on day h
        p50_net_qtl = p50 - costs.total_paise // qty_qtl
        gain_qtl = p50_net_qtl - sell_now_net_qtl

        # Worst-case net per quintal (p10)
        costs_p10 = compute_costs(p10, quantity_kg, distance_km, days=h)
        p10_net_qtl = p10 - costs_p10.total_paise // qty_qtl
        worst_qtl = p10_net_qtl - sell_now_net_qtl

        if gain_qtl > best_gain_qtl:
            best_day = h
            best_gain_qtl = gain_qtl
            best_worst_qtl = worst_qtl
            best_costs = costs
            best_p50_net_qtl = p50_net_qtl
            best_p10_net_qtl = p10_net_qtl

    # Convert to whole-lot paise for the response contract.
    best_gain_paise = best_gain_qtl * qty_qtl
    best_worst_paise = best_worst_qtl * qty_qtl

    # ── Gain-below-cost floor (whole lot) ──────────────────────────────
    if best_gain_paise < MIN_GAIN_PAISE:
        return WindowResult(
            action="SELL_NOW", hold_days=0, confidence="high",
            expected_gain_paise=0, worst_case_paise=0,
            refusal_reason=GAIN_BELOW_COST, band_width_bps=0,
            sell_now_net_paise_per_qtl=sell_now_net_qtl,
            hold_p50_net_paise_per_qtl=sell_now_net_qtl,
            hold_p10_net_paise_per_qtl=sell_now_net_qtl,
            costs=sell_now_costs,
            explain_mr="लवकर विकणे फायदेशीर आहे",
            explain_en="Selling now is more profitable than holding",
        )

    # ── Band-width check at chosen day ─────────────────────────────────
    p10_best, p50_best, p90_best = quantiles[best_day - 1]
    bw = _band_width_bps(p10_best, p50_best, p90_best)

    if bw > NO_ADVICE_BAND_BPS:
        return _no_advice(
            BAND_TOO_WIDE,
            f"भावातील अनिश्चितता खूप जास्त आहे ({bw // 100}%)",
            f"Forecast band too wide ({bw // 100}%); cannot advise",
        )

    # ── SPLIT check: if p10 scenario is worse than sell-now ────────────
    if best_worst_qtl < 0:
        action = "SPLIT"
        explain_mr = f"अर्धे आता विका, अर्धे {best_day} दिवस धरा — धोका आहे"
        explain_en = (f"Split: sell half now, hold half {best_day} days — "
                      f"downside risk exists")
        confidence = "medium"
    else:
        action = "HOLD"
        explain_mr = f"{best_day} दिवस धरा — अपेक्षित नफा ₹{best_gain_paise // 100}"
        explain_en = (f"Hold {best_day} days — expected net gain ₹{best_gain_paise // 100}")
        confidence = "high" if bw < 2000 else "medium"

    return WindowResult(
        action=action, hold_days=best_day, confidence=confidence,
        expected_gain_paise=best_gain_paise, worst_case_paise=best_worst_paise,
        refusal_reason=None, band_width_bps=bw,
        sell_now_net_paise_per_qtl=sell_now_net_qtl,
        hold_p50_net_paise_per_qtl=best_p50_net_qtl,
        hold_p10_net_paise_per_qtl=best_p10_net_qtl,
        costs=best_costs,
        explain_mr=explain_mr, explain_en=explain_en,
    )
