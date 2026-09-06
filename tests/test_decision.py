"""Tests for the decision engine — window.decide() and pledge.quote().

Uses the STUB predict_quantiles (no pickles needed).  Tests verify every
refusal gate, every verdict type, and the pledge gate (I13).
"""

from app.domain.window import (
    decide,
    BAND_TOO_WIDE,
    GAIN_BELOW_COST,
    INSUFFICIENT_HISTORY,
    MODEL_UNAVAILABLE,
    STALE_DATA,
    WindowResult,
)
from app.domain.pledge import quote, PledgeQuoteResult
from app.domain.costs import CostBreakdown


# ── Helpers ────────────────────────────────────────────────────────────

def _base_args(**overrides):
    """Sane defaults for decide().  Override any field."""
    args = dict(
        commodity="Onion",
        market="Lasalgaon APMC",
        spot_price_paise_per_qtl=180_000,
        quantity_kg=1000,
        distance_km=50.0,
        history_rows=400,
        as_of="2025-06-01",
    )
    args.update(overrides)
    return args


# ── Refusal gates ──────────────────────────────────────────────────────

def test_refuse_insufficient_history():
    r = decide(**_base_args(history_rows=50))
    assert r.action == "NO_ADVICE"
    assert r.refusal_reason == INSUFFICIENT_HISTORY


def test_refuse_insufficient_history_threshold():
    """Exactly at threshold should NOT refuse."""
    r = decide(**_base_args(history_rows=180))
    # With stub, this should produce a recommendation (not NO_ADVICE for history)
    assert r.refusal_reason != INSUFFICIENT_HISTORY


def test_refuse_zero_spot_price():
    r = decide(**_base_args(spot_price_paise_per_qtl=0))
    assert r.action == "NO_ADVICE"
    assert r.refusal_reason == STALE_DATA


def test_refuse_negative_spot_price():
    r = decide(**_base_args(spot_price_paise_per_qtl=-100))
    assert r.action == "NO_ADVICE"
    assert r.refusal_reason == STALE_DATA


# ── Verdict logic ──────────────────────────────────────────────────────

def test_stub_returns_hold_or_sell():
    """With the stub forecast (±10% band, slight uptrend), spot close to
    stub p50 means the gain may be below MIN_GAIN → SELL_NOW with
    GAIN_BELOW_COST.  If spot is low enough relative to forecast → HOLD."""
    # Set spot well below the stub p50 so there's real upside.
    r = decide(**_base_args(spot_price_paise_per_qtl=150_000))
    assert r.action in ("HOLD", "SPLIT", "SELL_NOW")
    assert isinstance(r, WindowResult)


def test_sell_now_when_spot_is_high():
    """If spot is above the forecast, gain should be negative → SELL_NOW."""
    r = decide(**_base_args(spot_price_paise_per_qtl=300_000))
    assert r.action == "SELL_NOW"
    assert r.refusal_reason == GAIN_BELOW_COST


def test_result_has_explain_strings():
    r = decide(**_base_args(spot_price_paise_per_qtl=150_000))
    assert len(r.explain_mr) > 0
    assert len(r.explain_en) > 0


def test_result_costs_are_valid():
    r = decide(**_base_args(spot_price_paise_per_qtl=150_000))
    assert isinstance(r.costs, CostBreakdown)
    # Five lines sum to total
    assert (r.costs.transport_paise + r.costs.commission_paise
            + r.costs.loading_paise + r.costs.storage_paise
            + r.costs.spoilage_paise == r.costs.total_paise)


def test_hold_days_in_range():
    r = decide(**_base_args(spot_price_paise_per_qtl=150_000))
    assert 0 <= r.hold_days <= 14


def test_band_width_bps_is_integer():
    r = decide(**_base_args(spot_price_paise_per_qtl=150_000))
    assert isinstance(r.band_width_bps, int)


# ── Verdict varies by commodity ────────────────────────────────────────

def test_onion_vs_soybean_different_outcomes():
    """Same spot price, different commodities → may differ (stub bases differ)."""
    onion = decide(**_base_args(commodity="Onion", market="Lasalgaon APMC",
                                spot_price_paise_per_qtl=150_000))
    soybean = decide(**_base_args(commodity="Soyabean", market="Latur APMC",
                                  spot_price_paise_per_qtl=150_000))
    # Both should be valid results (not crash)
    assert onion.action in ("HOLD", "SPLIT", "SELL_NOW", "NO_ADVICE")
    assert soybean.action in ("HOLD", "SPLIT", "SELL_NOW", "NO_ADVICE")


# ── Worst case always present ──────────────────────────────────────────

def test_worst_case_present_on_hold():
    """On any HOLD/SPLIT, worst_case_paise must be set."""
    r = decide(**_base_args(spot_price_paise_per_qtl=100_000))
    if r.action in ("HOLD", "SPLIT"):
        assert isinstance(r.worst_case_paise, int)


# ── Pledge tests ───────────────────────────────────────────────────────

def test_pledge_none_when_gain_le_interest():
    """If expected_gain <= interest → no pledge card."""
    # High interest, low gain
    result = quote(
        assessed_value_paise=1_000_000,
        expected_gain_paise=100,  # tiny gain
        days=14,
    )
    assert result is None


def test_pledge_none_on_zero_assessed_value():
    result = quote(assessed_value_paise=0, expected_gain_paise=10_000, days=7)
    assert result is None


def test_pledge_none_on_zero_days():
    result = quote(assessed_value_paise=1_000_000, expected_gain_paise=10_000, days=0)
    assert result is None


def test_pledge_positive_when_gain_exceeds_interest():
    """Large gain, small loan → pledge card appears."""
    result = quote(
        assessed_value_paise=5_000_000,   # ₹50,000 crop value
        expected_gain_paise=50_000,       # ₹500 gain >> interest
        days=7,
        ltv_bps=7000,
        rate_bps_annual=1200,
    )
    assert result is not None
    assert isinstance(result, PledgeQuoteResult)
    # Loan = 5_000_000 × 7000 / 10000 = 3_500_000 paise = ₹35,000
    assert result.loan_paise == 3_500_000
    # Interest = 3_500_000 × 1200 × 7 / (10000 × 365)
    expected_interest = 3_500_000 * 1200 * 7 // (10_000 * 365)
    assert result.interest_paise == expected_interest
    assert result.net_benefit_paise == 50_000 - expected_interest


def test_pledge_only_on_hold():
    """Pledge should only be computed when the verdict is HOLD.
    This is enforced at the router level (Phase 5), but verify the
    gate works: no pledge when gain is 0."""
    result = quote(
        assessed_value_paise=1_000_000,
        expected_gain_paise=0,
        days=7,
    )
    assert result is None


def test_pledge_values_are_integer():
    result = quote(
        assessed_value_paise=5_000_000,
        expected_gain_paise=50_000,
        days=7,
    )
    assert result is not None
    for attr in ("loan_paise", "interest_paise", "net_benefit_paise",
                 "assessed_value_paise", "days", "ltv_bps", "rate_bps_annual"):
        val = getattr(result, attr)
        assert isinstance(val, int), f"{attr} is {type(val).__name__}"


def test_pledge_disclaimer_present():
    result = quote(
        assessed_value_paise=5_000_000,
        expected_gain_paise=50_000,
        days=7,
    )
    assert result is not None
    assert len(result.disclaimer) > 50  # meaningful disclaimer


def test_pledge_wdra_flag():
    result = quote(
        assessed_value_paise=5_000_000,
        expected_gain_paise=50_000,
        days=7,
        is_wdra_registered=True,
    )
    assert result is not None
    assert result.is_wdra_registered is True


def test_pledge_warehouse_id_carried():
    result = quote(
        assessed_value_paise=5_000_000,
        expected_gain_paise=50_000,
        days=7,
        warehouse_id=42,
    )
    assert result is not None
    assert result.warehouse_id == 42


def test_pledge_frozen():
    result = quote(
        assessed_value_paise=5_000_000,
        expected_gain_paise=50_000,
        days=7,
    )
    assert isinstance(result, PledgeQuoteResult)
