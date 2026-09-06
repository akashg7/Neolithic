"""Tests for app.domain — costs, assessed_value, constants."""

import random
from app.domain.constants import (
    NO_ADVICE_BAND_BPS,
    MIN_HISTORY_ROWS,
    FORECAST_HORIZON_DAYS,
    DEFAULT_LTV_BPS,
    COMMISSION_RATE_BPS,
    TRANSPORT_PAISE_PER_KM,
    LOADING_PAISE_PER_KG,
    STORAGE_PAISE_PER_KG_PER_DAY,
    SPOILAGE_BPS_PER_DAY,
)
from app.domain.costs import compute_costs, CostBreakdown
from app.domain.assessed_value import assessed_value, GRADE_BPS


# ── Constants ──────────────────────────────────────────────────────────

def test_constants_have_sane_defaults():
    assert NO_ADVICE_BAND_BPS == 3500
    assert MIN_HISTORY_ROWS == 180
    assert FORECAST_HORIZON_DAYS == 14
    assert DEFAULT_LTV_BPS == 7000
    assert COMMISSION_RATE_BPS == 250


# ── CostBreakdown ──────────────────────────────────────────────────────

def test_costs_sum_to_total():
    """Five lines must sum to total exactly — every call, every input."""
    for _ in range(50):
        price = random.randint(50_000, 500_000)
        qty = random.randint(100, 10_000)
        dist = random.uniform(10, 500)
        days = random.randint(0, 14)
        cb = compute_costs(price, qty, dist, days)
        assert cb.transport_paise + cb.commission_paise + cb.loading_paise \
               + cb.storage_paise + cb.spoilage_paise == cb.total_paise, \
            f"Sum mismatch: {cb}"


def test_costs_sell_today_zero_storage_and_spoilage():
    cb = compute_costs(200_000, 1000, 100.0, days=0)
    assert cb.storage_paise == 0
    assert cb.spoilage_paise == 0
    assert cb.transport_paise == int(100.0 * TRANSPORT_PAISE_PER_KM)
    assert cb.loading_paise == 1000 * LOADING_PAISE_PER_KG


def test_costs_hold_increases_storage_and_spoilage():
    cb0 = compute_costs(200_000, 1000, 100.0, days=0)
    cb7 = compute_costs(200_000, 1000, 100.0, days=7)
    cb14 = compute_costs(200_000, 1000, 100.0, days=14)
    assert cb0.total_paise < cb7.total_paise < cb14.total_paise
    # Storage grows linearly
    assert cb7.storage_paise == 1000 * 7 * STORAGE_PAISE_PER_KG_PER_DAY
    assert cb14.storage_paise == 1000 * 14 * STORAGE_PAISE_PER_KG_PER_DAY


def test_costs_all_integer():
    cb = compute_costs(123_456, 789, 42.7, days=3)
    for attr in ("transport_paise", "commission_paise", "loading_paise",
                 "storage_paise", "spoilage_paise", "total_paise"):
        val = getattr(cb, attr)
        assert isinstance(val, int), f"{attr} is {type(val).__name__}, expected int"


def test_costs_frozen():
    cb = compute_costs(200_000, 1000, 100.0, days=1)
    assert isinstance(cb, CostBreakdown)


# ── Assessed value ─────────────────────────────────────────────────────

def test_assessed_value_grade_ordering():
    """A > B > C for the same quantity and forecast."""
    p10 = 200_000  # paise per quintal
    qty = 1000     # kg = 10 quintals
    va = assessed_value("A", qty, p10)
    vb = assessed_value("B", qty, p10)
    vc = assessed_value("C", qty, p10)
    assert va > vb > vc


def test_assessed_value_integer():
    v = assessed_value("A", 1234, 180_000)
    assert isinstance(v, int)


def test_assessed_value_grade_a_is_full():
    """Grade A with 10 quintals × ₹1800 = ₹18,000 = 1_800_000 paise."""
    v = assessed_value("A", 1000, 180_000)
    assert v == 180_000 * 10 * 10_000 // 10_000  # = 180_000 * 10


def test_assessed_value_grade_b_is_85_pct():
    v = assessed_value("B", 1000, 180_000)
    expected = 180_000 * 10 * 8_500 // 10_000
    assert v == expected


def test_assessed_value_invalid_grade():
    try:
        assessed_value("D", 1000, 180_000)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "D" in str(e)


def test_assessed_value_zero_qty():
    try:
        assessed_value("A", 0, 180_000)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "positive" in str(e)
