"""
Training Pipeline for LightGBM Quantile Models (Person A)

Trains direct multi-horizon models (14 separate day-models) pooled by commodity:
- For h in 1..14: target = ModalPrice.shift(-h) in integer paise
- For alpha in {0.10, 0.50, 0.90}: LGBMRegressor(objective='quantile', alpha=alpha)
- Hyperparameters: num_leaves=31, min_child_samples=20, n_estimators=300,
  lr=0.05, subsample=0.8, colsample_bytree=0.8, random_state=42
- Bundles {(h, alpha): model}, feature names, and metadata -> artifacts/{commodity}.pkl
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Tuple
import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor

from app.ml import ARTIFACT_DIR, SNAPSHOT_DIR, FORECAST_HORIZON_DAYS, QUANTILE_ALPHAS, CORE_SERIES, pooled_mandis
from app.ml.features import derive_features, FEATURE_COLS, CATEGORICAL_COLS

logger = logging.getLogger(__name__)


def prepare_training_data(
    df: pd.DataFrame,
    commodity: str,
    horizon: int = FORECAST_HORIZON_DAYS,
) -> Tuple[pd.DataFrame, Dict[str, int], Dict[str, int]]:
    """Filter to commodity, derive features, and construct multi-horizon paise targets."""
    comm_mandis = pooled_mandis(commodity)
    df_comm = df[(df["Commodity"] == commodity) & (df["Mandi"].isin(comm_mandis))].copy()
    df_comm = df_comm.sort_values(by=["Mandi", "date"]).reset_index(drop=True)

    # Derive backward-looking features
    df_feat, m_map, d_map = derive_features(df_comm)

    # Construct multi-horizon targets in paise (ModalPrice in ₹ * 100)
    groups = df_feat.groupby("Mandi", group_keys=False)
    for h in range(1, horizon + 1):
        target_paise = groups["ModalPrice"].shift(-h) * 100.0
        df_feat[f"target_h_{h}"] = target_paise

    return df_feat, m_map, d_map


def train_commodity_models(
    df: pd.DataFrame,
    commodity: str,
    horizon: int = FORECAST_HORIZON_DAYS,
    alphas: Tuple[float, ...] = QUANTILE_ALPHAS,
    max_train_date: str | None = None,
) -> Dict[str, Any]:
    """Train direct multi-horizon quantile models for a commodity.

    Parameters
    ----------
    df : pd.DataFrame
        Clean snapshot DataFrame.
    commodity : str
        Commodity name (e.g. "Onion", "Soyabean").
    horizon : int
        Number of forecast horizons (default 14).
    alphas : tuple of float
        Quantiles to train (default (0.10, 0.50, 0.90)).
    max_train_date : str, optional
        If provided, trains only on data up to this calendar date (for backtesting).

    Returns
    -------
    bundle dict containing trained models and metadata.
    """
    df_feat, m_map, d_map = prepare_training_data(df, commodity, horizon)

    if max_train_date is not None:
        train_mask = df_feat["date"] <= pd.to_datetime(max_train_date)
    else:
        train_mask = pd.Series(True, index=df_feat.index)

    models: Dict[Tuple[int, float], LGBMRegressor] = {}
    rows_used = 0

    for h in range(1, horizon + 1):
        target_col = f"target_h_{h}"
        # Only use rows where the target is not NaN (cannot evaluate beyond dataset end)
        valid_mask = train_mask & df_feat[target_col].notna()
        sub = df_feat[valid_mask]
        if len(sub) == 0:
            continue

        X = sub[FEATURE_COLS]
        y = sub[target_col].to_numpy()
        rows_used = max(rows_used, len(X))

        for alpha in alphas:
            reg = LGBMRegressor(
                objective="quantile",
                alpha=alpha,
                num_leaves=31,
                min_child_samples=20,
                n_estimators=300,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                verbosity=-1,
                n_jobs=-1,
            )
            reg.fit(X, y, categorical_feature=CATEGORICAL_COLS)
            models[(h, alpha)] = reg

    bundle = {
        "commodity": commodity,
        "models": models,
        "feature_names": FEATURE_COLS,
        "categorical_features": CATEGORICAL_COLS,
        "mandi_mapping": m_map,
        "district_mapping": d_map,
        "pooled_mandis": pooled_mandis(commodity),
        "horizon": horizon,
        "alphas": list(alphas),
        "training_rows": rows_used,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "data_source": "real",
    }
    return bundle


def save_artifact(bundle: Dict[str, Any], filepath: Path | None = None) -> Path:
    """Save model bundle to artifacts directory."""
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    commodity = bundle["commodity"]
    out_path = filepath or (ARTIFACT_DIR / f"{commodity}.pkl")
    joblib.dump(bundle, out_path, compress=3)
    logger.info("Saved %s model bundle to %s (%d models, %.2f MB)",
                commodity, out_path, len(bundle["models"]), out_path.stat().st_size / (1024 * 1024))
    return out_path


if __name__ == "__main__":
    snapshot_csv = SNAPSHOT_DIR / "core_series.csv"
    if not snapshot_csv.exists():
        raise FileNotFoundError(f"Snapshot CSV missing: {snapshot_csv}")

    df_snap = pd.read_csv(snapshot_csv)
    for comm in ["Onion", "Soyabean"]:
        logger.info("Training %s models...", comm)
        b = train_commodity_models(df_snap, comm)
        save_artifact(b)
        logger.info("Finished training %s.", comm)
