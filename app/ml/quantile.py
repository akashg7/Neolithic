"""
Quantile prediction interface — the FROZEN contract between the ML lane (Person A)
and the decision lane (Person B).

Person B codes against `predict_quantiles` and `ModelUnavailable` only.
The real implementation (pickle-loaded LightGBM models) replaces the stub
in Phase 4; until then the stub returns clearly-marked PLACEHOLDER values.

Do NOT edit this module's public API without both-person agreement.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from pathlib import Path

from app.ml import ARTIFACT_DIR, FORECAST_HORIZON_DAYS, QUANTILE_ALPHAS

logger = logging.getLogger(__name__)


# ── Exception (Person B catches this — never lets it become a 500) ─────
class ModelUnavailable(Exception):
    """Raised when the requested commodity model has not been trained/loaded."""

    def __init__(self, key: str):
        self.key = key
        super().__init__(f"Model not available for: {key}")


# ── Internal state ─────────────────────────────────────────────────────
_models: dict[str, object] = {}          # commodity -> bundled model dict
_feature_names: list[str] = []           # frozen after load
_is_loaded: bool = False


def load_models() -> None:
    """Called once at FastAPI startup (lifespan).

    Loads every `artifacts/{commodity}.pkl` into memory.
    No-ops silently if artifacts/ is empty (stub mode).
    """
    global _is_loaded, _feature_names

    if not ARTIFACT_DIR.exists():
        logger.warning("artifacts/ not found — running in STUB mode (no pickles loaded).")
        _is_loaded = True
        return

    import joblib

    loaded = 0
    for pkl in ARTIFACT_DIR.glob("*.pkl"):
        commodity = pkl.stem
        bundle = joblib.load(pkl)
        _models[commodity] = bundle
        if not _feature_names:
            _feature_names = bundle.get("feature_names", [])
        loaded += 1
        logger.info("Loaded model: %s (%d horizons × %d quantiles)",
                     commodity, bundle.get("horizon", FORECAST_HORIZON_DAYS),
                     len(QUANTILE_ALPHAS))

    if loaded:
        logger.info("All models loaded (%d commodities). Feature count: %d",
                     loaded, len(_feature_names))
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
    market_key = market.strip()

    # ── STUB mode: no pickles loaded at all ────────────────────────────
    if not _models:
        return _stub_predict(commodity_key, horizon)

    # ── Models loaded but commodity not found ──────────────────────────
    if commodity_key not in _models:
        raise ModelUnavailable(commodity_key)

    # ── Real implementation (Phase 4 — replace this block) ─────────────
    # bundle = _models[commodity_key]
    # ... build features for (market_key, as_of) ...
    # ... call bundle[(h, alpha)].predict(X) for each h, alpha ...
    # ... return sorted [(p10, p50, p90)] per horizon day ...
    raise NotImplementedError(
        "Models loaded but predict_quantiles body not yet wired. "
        "Phase 4 integration pending."
    )


# ── Stub internals (deleted after Phase 4) ─────────────────────────────
_STUB_BASES = {
    "Onion":    180_000,   # paise per quintal — realistic Lasalgaon median
    "Soyabean": 380_000,   # paise per quintal — realistic Latur median
}


def _stub_predict(commodity: str, horizon: int) -> list[tuple[int, int, int]]:
    """Return clearly-marked PLACEHOLDER quantiles.  Tests may assert these
    are *not* present in production by grepping for 'STUB' in logs."""
    base = _STUB_BASES.get(commodity, 200_000)
    spread = int(base * 0.10)  # ±10 %
    results: list[tuple[int, int, int]] = []
    for h in range(1, horizon + 1):
        # Slight upward drift so it doesn't look completely flat.
        drift = int(base * 0.002 * h)
        p50 = base + drift
        p10 = p50 - spread
        p90 = p50 + spread
        results.append((p10, p50, p90))
    logger.debug("STUB predict: %s × %d days → %s", commodity, horizon, results[:2])
    return results
