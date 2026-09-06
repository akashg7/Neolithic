"""
Training & Backtesting Orchestrator (Person A)

Executes the complete ML training and walk-forward backtesting pipeline:
1. Loads clean snapshot from app/ml/snapshots/core_series.csv
2. Trains direct multi-horizon LightGBM quantile models for Onion & Soyabean
3. Saves model pickles to app/ml/artifacts/{commodity}.pkl
4. Executes expanding-window walk-forward backtest (evaluating per-mandi and pooled)
5. Exports evaluation details to artifacts/walkforward.json
6. Generates and persists model card metadata to artifacts/model_meta.json
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
import pandas as pd

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.ml import SNAPSHOT_DIR, ARTIFACT_DIR, COMMODITIES
from app.ml.train import train_commodity_models, save_artifact
from app.ml.backtest import run_walk_forward_backtest
from app.ml.walkforward_export import export_walkforward_json
from app.ml.model_card import build_model_card, save_model_meta


def main() -> None:
    snapshot_csv = SNAPSHOT_DIR / "core_series.csv"
    if not snapshot_csv.exists():
        logger.error("Snapshot CSV missing at %s. Run scripts/ingest_csv.py first.", snapshot_csv)
        sys.exit(1)

    logger.info("Loading snapshot data from %s ...", snapshot_csv)
    df_snap = pd.read_csv(snapshot_csv)
    logger.info("Loaded %d rows for training and validation.", len(df_snap))

    model_cards = {}

    for commodity in COMMODITIES:
        logger.info("\n" + "=" * 60)
        logger.info("PROCESSING COMMODITY: %s", commodity.upper())
        logger.info("=" * 60)

        # 1. Train models on full dataset
        logger.info("Training full %s model bundle (14 horizons × 3 quantiles)...", commodity)
        bundle = train_commodity_models(df_snap, commodity)
        pkl_path = save_artifact(bundle)
        logger.info("Saved %s artifact to: %s", commodity, pkl_path)

        # 2. Walk-forward backtest
        logger.info("Running walk-forward backtest for %s...", commodity)
        bt_results = run_walk_forward_backtest(df_snap, commodity, n_windows=5)

        # 3. Export walk-forward evaluation points
        wf_path = export_walkforward_json(bt_results)

        # 4. Generate model card
        card = build_model_card(commodity, bundle, bt_results)
        model_cards[commodity] = card

        # Print summary
        print(f"\n--- {commodity} Performance Summary ---")
        print(f"Pooled MASE: {card['mase_pooled']:.3f} (Seasonal-naive lag-7 baseline = 1.000)")
        print(f"Pooled Coverage: {card['coverage_bps_pooled'] / 100:.1f}% ({card['coverage_bps_pooled']} bps)")
        print("Per-Mandi Breakdown:")
        print(f"{'Mandi':<25} | {'MASE':<8} | {'Coverage (bps)':<15} | {'Coverage (%)'}")
        print("-" * 65)
        for m in sorted(card["mase_per_mandi"].keys()):
            mase_val = card["mase_per_mandi"][m]
            cov_bps = card["coverage_bps_per_mandi"].get(m, 0)
            cov_pct = cov_bps / 100.0
            print(f"{m:<25} | {mase_val:<8.3f} | {cov_bps:<15d} | {cov_pct:.1f}%")

    # 5. Save model metadata
    save_model_meta(model_cards)
    logger.info("\nAll training and backtesting artifacts successfully saved to: %s", ARTIFACT_DIR)


if __name__ == "__main__":
    main()
