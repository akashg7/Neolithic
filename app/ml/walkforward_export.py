"""
Walk-Forward Export Pipeline (Person A)

Persists walk-forward evaluation points to `artifacts/walkforward.json`.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Any

from app.ml import ARTIFACT_DIR

logger = logging.getLogger(__name__)


def export_walkforward_json(
    backtest_results: Dict[str, Any],
    filepath: Path | None = None,
) -> Path:
    """Export walkforward points to JSON."""
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = filepath or (ARTIFACT_DIR / "walkforward.json")

    # If file exists, merge commodities
    existing = {}
    if out_path.exists():
        try:
            existing = json.loads(out_path.read_text(encoding="utf-8"))
        except Exception:
            existing = {}

    commodity = backtest_results["commodity"]
    existing[commodity] = {
        "mase_pooled": backtest_results["mase_pooled"],
        "coverage_bps_pooled": backtest_results["coverage_bps_pooled"],
        "mase_per_mandi": backtest_results["mase_per_mandi"],
        "coverage_bps_per_mandi": backtest_results["coverage_bps_per_mandi"],
        "points": backtest_results["walkforward_points"],
    }

    out_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")
    logger.info("Saved walk-forward data to %s (%.2f KB, %d points for %s)",
                out_path, out_path.stat().st_size / 1024, len(backtest_results["walkforward_points"]), commodity)
    return out_path
