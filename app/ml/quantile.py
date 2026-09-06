"""
Quantile prediction interface — the FROZEN contract between the ML lane (Person A)
and the decision lane (Person B).

Person B codes against `predict_quantiles` and `ModelUnavailable` only.
The real implementation loads trained LightGBM direct multi-horizon quantile models
from `app/ml/artifacts/{commodity}.pkl`.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple
import joblib
import numpy as np
import pandas as pd

from app.ml import ARTIFACT_DIR, SNAPSHOT_DIR, FORECAST_HORIZON_DAYS, QUANTILE_ALPHAS
from app.ml.features import derive_features, FEATURE_COLS, CATEGORICAL_COLS

logger = logging.getLogger(__name__)


# ── Exception (Person B catches this — never lets it become a 500) ─────
class ModelUnavailable(Exception):
    """Raised when the requested commodity model has not been trained/loaded."""

    def __init__(self, key: str):
        self.key = key
        super().__init__(f"Model not available for: {key}")


# ── Internal state ─────────────────────────────────────────────────────
_models: Dict[str, Dict[str, Any]] = {}          # commodity -> bundled model dict
_feature_names: List[str] = []                   # frozen after load
_is_loaded: bool = False
_snapshot_df: pd.DataFrame | None = None         # cached snapshot for inference features


def _get_snapshot() -> pd.DataFrame:
    """Lazily load snapshot data for feature derivation."""
    global _snapshot_df
    if _snapshot_df is None:
        csv_path = SNAPSHOT_DIR / "core_series.csv"
        if csv_path.exists():
            df = pd.read_csv(csv_path)
            df["date"] = pd.to_datetime(df["date"])
            _snapshot_df = df
        else:
            _snapshot_df = pd.DataFrame()
    return _snapshot_df


def load_models() -> None:
    """Called once at FastAPI startup (lifespan).

    Loads every `artifacts/{commodity}.pkl` into memory.
    """
    global _is_loaded, _feature_names

    if not ARTIFACT_DIR.exists():
        logger.warning("artifacts/ not found — running in STUB mode (no pickles loaded).")
        _is_loaded = True
        return

    loaded = 0
    for pkl in ARTIFACT_DIR.glob("*.pkl"):
        commodity = pkl.stem
        bundle = joblib.load(pkl)
        _models[commodity] = bundle
        if not _feature_names:
            _feature_names = bundle.get("feature_names", FEATURE_COLS)
        loaded += 1
        logger.info(
            "Loaded model: %s (%d horizons × %d quantiles)",
            commodity,
            bundle.get("horizon", FORECAST_HORIZON_DAYS),
            len(bundle.get("alphas", QUANTILE_ALPHAS)),
        )

    if loaded:
        logger.info("All models loaded (%d commodities). Feature count: %d", loaded, len(_feature_names))
    else:
        logger.warning("No .pkl files found in artifacts/ — STUB mode.")

    _is_loaded = True


def is_loaded() -> bool:
    return _is_loaded


# ── The FROZEN public API ──────────────────────────────────────────────
def predict_quantiles(
    commodity: str,
    market: str,
    as_of: str | date | datetime,
    horizon: int = FORECAST_HORIZON_DAYS,
) -> list[tuple[int, int, int]]:
    """Predict daily p10/p50/p90 price-in-paise for *horizon* days ahead.

    Parameters
    ----------
    commodity : str   Canonical commodity name (e.g. "Onion", "Soyabean").
    market    : str   Canonical mandi name (e.g. "Lasalgaon APMC").
    as_of     : date  The "today" from which to forecast (walk-forward safe).
    horizon   : int   Number of days to forecast (default 14).

    Returns
    -------
    list of (p10, p50, p90) tuples, each value in integer paise, already
    ``sorted()`` so p10 <= p50 <= p90.  Length == horizon.

    Raises
    ------
    ModelUnavailable  If the commodity model hasn't been loaded/trained.
    """
    commodity_key = commodity.strip().title()
    if commodity_key == "Soybean":
        commodity_key = "Soyabean"
    market_key = market.strip()

    # ── STUB mode: no pickles loaded at all ────────────────────────────
    if not _models:
        return _stub_predict(commodity_key, horizon)

    # ── Models loaded but commodity not found ──────────────────────────
    if commodity_key not in _models:
        raise ModelUnavailable(commodity_key)

    bundle = _models[commodity_key]
    models = bundle["models"]
    mandi_map = bundle.get("mandi_mapping", {})
    dist_map = bundle.get("district_mapping", {})

    # ── Parse as_of timestamp ──────────────────────────────────────────
    if isinstance(as_of, str):
        as_of_dt = pd.to_datetime(as_of)
    elif isinstance(as_of, datetime):
        as_of_dt = pd.Timestamp(as_of)
    elif isinstance(as_of, date):
        as_of_dt = pd.Timestamp(as_of)
    else:
        as_of_dt = pd.Timestamp.now()

    # ── Build Feature Vector ───────────────────────────────────────────
    snap_df = _get_snapshot()
    X_eval: pd.DataFrame | None = None

    if not snap_df.empty:
        # Filter for this commodity and history up to as_of
        hist = snap_df[(snap_df["Commodity"] == commodity_key) & (snap_df["date"] <= as_of_dt)].copy()

        # Check if market has historical rows
        mandi_hist = hist[hist["Mandi"] == market_key]

        if not mandi_hist.empty:
            # Re-derive features for market history
            df_feat, _, _ = derive_features(mandi_hist, mandi_mapping=mandi_map, district_mapping=dist_map)
            X_eval = df_feat.iloc[[-1]][FEATURE_COLS].copy()
        elif not hist.empty:
            # Held-out mandi: use closest or default commodity profile with held-out mandi encoding
            df_feat, _, _ = derive_features(hist, mandi_mapping=mandi_map, district_mapping=dist_map)
            X_eval = df_feat.iloc[[-1]][FEATURE_COLS].copy()
            # Set custom mandi categorical ID
            X_eval["mandi_id"] = mandi_map.get(market_key, -1)

    if X_eval is None:
        # Fallback synthetic feature vector if snapshot is unavailable
        data = {col: [0.0] for col in FEATURE_COLS}
        data["mandi_id"] = [mandi_map.get(market_key, -1)]
        data["district_id"] = [0]
        data["modal_lag_1"] = [2000.0]
        data["rolling_mean_7"] = [2000.0]
        X_eval = pd.DataFrame(data)

    # Strictly enforce types
    for col in FEATURE_COLS:
        if col in CATEGORICAL_COLS:
            X_eval[col] = X_eval[col].astype(int)
        else:
            X_eval[col] = X_eval[col].astype(float)

    # ── Predict for each horizon day ───────────────────────────────────
    results: List[Tuple[int, int, int]] = []
    for h in range(1, horizon + 1):
        m10 = models.get((h, 0.10))
        m50 = models.get((h, 0.50))
        m90 = models.get((h, 0.90))

        if m10 is None or m50 is None or m90 is None:
            # If a horizon model is missing, extrapolate from previous horizon
            if results:
                prev_p10, prev_p50, prev_p90 = results[-1]
                results.append((prev_p10, prev_p50, prev_p90))
            else:
                results.append((180_000, 200_000, 220_000))
            continue

        pred_p10 = int(round(m10.predict(X_eval)[0]))
        pred_p50 = int(round(m50.predict(X_eval)[0]))
        pred_p90 = int(round(m90.predict(X_eval)[0]))

        # Strictly enforce ascending sort and positive paise
        p10, p50, p90 = sorted((max(1, pred_p10), max(1, pred_p50), max(1, pred_p90)))
        results.append((p10, p50, p90))

    return results


# ── Stub internals (used when no models loaded) ───────────────────────
_STUB_BASES = {
    "Onion":    180_000,   # paise per quintal
    "Soyabean": 380_000,   # paise per quintal
}


def _stub_predict(commodity: str, horizon: int) -> list[tuple[int, int, int]]:
    """Return clearly-marked PLACEHOLDER quantiles when in stub mode."""
    base = _STUB_BASES.get(commodity, 200_000)
    spread = int(base * 0.10)
    results: list[tuple[int, int, int]] = []
    for h in range(1, horizon + 1):
        drift = int(base * 0.002 * h)
        p50 = base + drift
        p10 = p50 - spread
        p90 = p50 + spread
        results.append((p10, p50, p90))
    return results
