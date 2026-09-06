"""
Demo Replay Spotlight Generator (Person A)

Selects 3 illustrative spotlight dates from the honest walk-forward evaluation dataset
(`artifacts/walkforward.json`) and emits `artifacts/demo_replay.json`:
1. Spotlight 1 (Soyabean): Latur APMC (2026-06-04) — Calibrated HOLD that worked (MASE 0.473, 100% containment).
2. Spotlight 2 (Onion): Lasalgaon APMC (2026-05-02) — High accuracy seasonal forecast (MASE 0.204, 85.7% containment).
3. Spotlight 3 (Onion Uncertainty): Lasalgaon APMC (2026-08-19) — Late-monsoon price swing triggering wide band / NO_ADVICE.

Integrity Rule:
Spotlight dates are a filter over the honest walk-forward dataset, NEVER a re-run or synthetic cherry-pick.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import List

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.ml import ARTIFACT_DIR
from app.ml._contract import ReplayPoint

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def generate_demo_replay() -> Path:
    wf_path = ARTIFACT_DIR / "walkforward.json"
    if not wf_path.exists():
        raise FileNotFoundError(f"walkforward.json not found at {wf_path}. Run scripts/train_and_backtest.py first.")

    with open(wf_path, "r", encoding="utf-8") as f:
        wf_data = json.load(f)

    spotlight_targets = [
        # 1. Soyabean: Latur APMC (2026-06-04) - Confident, calibrated hold
        {"commodity": "Soyabean", "market": "Latur APMC", "cutoff_date": "2026-06-04"},
        # 2. Onion: Lasalgaon APMC (2026-05-02) - High-confidence seasonal hold
        {"commodity": "Onion", "market": "Lasalgaon APMC", "cutoff_date": "2026-05-02"},
        # 3. Onion: Lasalgaon APMC (2026-08-19) - Late-monsoon volatility / wide band
        {"commodity": "Onion", "market": "Lasalgaon APMC", "cutoff_date": "2026-08-19"},
    ]

    selected_points: List[ReplayPoint] = []

    for target in spotlight_targets:
        comm = target["commodity"]
        comm_points = wf_data.get(comm, {}).get("points", [])
        matched = None
        for p in comm_points:
            if p["market"] == target["market"] and p["cutoff_date"] == target["cutoff_date"]:
                matched = p
                break

        if matched:
            selected_points.append(matched)
            logger.info("Found spotlight point: %s %s on %s (MASE: %.3f, Coverage: %d bps)",
                        comm, target["market"], target["cutoff_date"],
                        matched["mase_at_cutoff"], matched["coverage_at_cutoff_bps"])
        else:
            logger.warning("Target spotlight %s not found in walkforward points", target)

    out_path = ARTIFACT_DIR / "demo_replay.json"
    out_path.write_text(json.dumps(selected_points, indent=2), encoding="utf-8")
    logger.info("Emitted %d spotlight replay points to %s (%.2f KB)",
                len(selected_points), out_path, out_path.stat().st_size / 1024)
    return out_path


if __name__ == "__main__":
    generate_demo_replay()
