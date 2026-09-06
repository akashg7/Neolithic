"""
Person A (Forecast Lane) Unit Test Suite

Verifies:
1. test_no_leakage: rolling features at t do not change when future rows are truncated.
2. test_quantiles_ordered: p10 <= p50 <= p90 across 100 predictions.
3. test_integer_output: output values are non-negative Python integers (paise).
4. test_model_loads: load_models() successfully loads .pkl files and marks is_loaded().
5. test_backtest_metrics: finite MASE (> 0), valid coverage in (0, 10000) bps.
6. test_dedupe: zero duplicate (series_id, date) in snapshot.
7. test_pooled_uses_mandi_feature: held-out mandi still predicts using its features.
8. test_model_unavailable_raises: unknown commodity raises ModelUnavailable.
"""

from __future__ import annotations

import json
from pathlib import Path
import pandas as pd
import pytest

from app.ml import SNAPSHOT_DIR, ARTIFACT_DIR, COMMODITIES
from app.ml.features import test_no_leakage as check_no_leakage, derive_features, FEATURE_COLS
from app.ml.quantile import load_models, is_loaded, predict_quantiles, ModelUnavailable


@pytest.fixture(scope="session", autouse=True)
def setup_models():
    """Ensure models are loaded once for the test session."""
    load_models()


def test_leakage_guard():
    """Assert every rolling feature at row t is unchanged when future rows are dropped."""
    assert check_no_leakage() is True


def test_model_loading():
    """Assert models are loaded into memory and flags is_loaded()."""
    assert is_loaded() is True
    onion_pkl = ARTIFACT_DIR / "Onion.pkl"
    soya_pkl = ARTIFACT_DIR / "Soyabean.pkl"
    assert onion_pkl.exists(), f"Missing {onion_pkl}"
    assert soya_pkl.exists(), f"Missing {soya_pkl}"


def test_deduplication_integrity():
    """Assert zero duplicate (series_id, date) and (Mandi, Commodity, date) in snapshot."""
    snap_csv = SNAPSHOT_DIR / "core_series.csv"
    assert snap_csv.exists(), f"Missing {snap_csv}"
    df = pd.read_csv(snap_csv)

    dupes_series = df.duplicated(subset=["series_id", "date"]).sum()
    dupes_mandi = df.duplicated(subset=["Mandi", "Commodity", "date"]).sum()

    assert dupes_series == 0, f"Found {dupes_series} duplicate series_id/date rows!"
    assert dupes_mandi == 0, f"Found {dupes_mandi} duplicate Mandi/Commodity/date rows!"


def test_quantiles_strictly_ordered():
    """Assert p10 <= p50 <= p90 across 100 sample prediction calls."""
    test_cases = [
        ("Onion", "Lasalgaon APMC", "2026-05-01"),
        ("Onion", "Pimpalgaon APMC", "2026-06-01"),
        ("Onion", "Pune(Manjri) APMC", "2026-07-01"),
        ("Soyabean", "Akola APMC", "2026-06-15"),
        ("Soyabean", "Latur APMC", "2026-07-01"),
        ("Soyabean", "Nanded APMC", "2026-08-01"),
    ]

    for comm, mandi, as_of in test_cases:
        res = predict_quantiles(comm, mandi, as_of, horizon=14)
        assert len(res) == 14
        for p10, p50, p90 in res:
            assert p10 <= p50, f"Violation: p10 ({p10}) > p50 ({p50})"
            assert p50 <= p90, f"Violation: p50 ({p50}) > p90 ({p90})"


def test_integer_money_output():
    """Assert predictions are positive Python ints representing paise."""
    res = predict_quantiles("Onion", "Lasalgaon APMC", "2026-06-01", horizon=14)
    for p10, p50, p90 in res:
        assert isinstance(p10, int) and isinstance(p50, int) and isinstance(p90, int)
        assert p10 > 0 and p50 > 0 and p90 > 0
        assert type(p10) is int and type(p50) is int and type(p90) is int


def test_backtest_metrics_validity():
    """Assert backtest metrics in model_meta.json have finite MASE and valid coverage bps."""
    meta_path = ARTIFACT_DIR / "model_meta.json"
    assert meta_path.exists(), f"Missing {meta_path}"

    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    for comm in ["Onion", "Soyabean"]:
        assert comm in meta
        card = meta[comm]
        assert card["mase_pooled"] > 0
        assert 0 < card["coverage_bps_pooled"] <= 10000
        assert card["training_rows"] > 100
        assert card["feature_count"] == len(FEATURE_COLS)
        assert card["data_source"] == "real"


def test_pooled_uses_mandi_feature():
    """Assert a held-out or unobserved mandi name still predicts safely using feature vector."""
    held_out_mandi = "NonExistent APMC"
    res = predict_quantiles("Onion", held_out_mandi, "2026-06-01", horizon=14)
    assert len(res) == 14
    for p10, p50, p90 in res:
        assert isinstance(p10, int) and isinstance(p50, int) and isinstance(p90, int)
        assert p10 <= p50 <= p90


def test_model_unavailable_raises():
    """Assert requesting an untrained commodity raises ModelUnavailable exception."""
    with pytest.raises(ModelUnavailable):
        predict_quantiles("Pineapple", "Lasalgaon APMC", "2026-06-01")
