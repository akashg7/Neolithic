"""
Model Card Generator & Metadata Persistence (Person A)

Generates structured provenance and performance metadata matching the
`ModelCard` TypedDict in `app/ml/_contract.py`:
- Saves to `app/ml/artifacts/model_meta.json`
- Generates human-readable markdown summaries
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, Any, List

from app.ml import ARTIFACT_DIR
from app.ml._contract import ModelCard

logger = logging.getLogger(__name__)


KNOWN_LIMITATIONS = {
    "Onion": [
        "Highly sensitive to sudden unseasonal rains and monsoon transport disruption.",
        "Spot prices move >40% in single days during rabi storage transitions; band appropriately widens.",
        "Market holidays (Sundays, national festivals) cause trading pauses where prices hold constant.",
    ],
    "Soyabean": [
        "Historical tracking begins September 2025 (~1 year of observations).",
        "Nanded APMC history currently has <180 trading days; the system appropriately issues INSUFFICIENT_HISTORY refusal.",
        "Sensitive to global edible oil import duty adjustments and monsoon pod-filling weather anomalies.",
    ],
}


def build_model_card(
    commodity: str,
    bundle: Dict[str, Any],
    backtest_results: Dict[str, Any],
) -> ModelCard:
    """Construct ModelCard dictionary matching Phase 0 frozen contract."""
    card: ModelCard = {
        "commodity": commodity,
        "pooled_mandis": bundle.get("pooled_mandis", []),
        "training_rows": int(bundle.get("training_rows", 0)),
        "feature_count": len(bundle.get("feature_names", [])),
        "mase_pooled": float(backtest_results.get("mase_pooled", 1.0)),
        "mase_per_mandi": {k: float(v) for k, v in backtest_results.get("mase_per_mandi", {}).items()},
        "coverage_bps_pooled": int(backtest_results.get("coverage_bps_pooled", 8000)),
        "coverage_bps_per_mandi": {k: int(v) for k, v in backtest_results.get("coverage_bps_per_mandi", {}).items()},
        "horizon_days": int(bundle.get("horizon", 14)),
        "quantile_alphas": [float(a) for a in bundle.get("alphas", [0.10, 0.50, 0.90])],
        "trained_at": str(bundle.get("trained_at", "")),
        "data_source": str(bundle.get("data_source", "real")),
        "known_limitations": KNOWN_LIMITATIONS.get(commodity, []),
    }
    return card


def save_model_meta(cards: Dict[str, ModelCard], filepath: Path | None = None) -> Path:
    """Save model metadata dictionary to artifacts/model_meta.json."""
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = filepath or (ARTIFACT_DIR / "model_meta.json")

    # If file exists, merge
    existing = {}
    if out_path.exists():
        try:
            existing = json.loads(out_path.read_text(encoding="utf-8"))
        except Exception:
            existing = {}

    for k, v in cards.items():
        existing[k] = v

    out_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")
    logger.info("Saved model card metadata to %s", out_path)
    return out_path
