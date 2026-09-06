"""
Walk-Forward Backtesting Pipeline (Person A)

Performs expanding-window walk-forward evaluation on global calendar dates:
- Evaluates per-mandi and pooled MASE vs seasonal-naive lag-7 benchmark
- Computes empirical p10-p90 coverage (expressed in basis points)
- Saves detailed walk-forward forecast points for demo replay and verification
"""

from __future__ import annotations

import logging
from typing import Dict, List, Any, Tuple
import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor

from app.ml import FORECAST_HORIZON_DAYS, QUANTILE_ALPHAS, CORE_SERIES, pooled_mandis
from app.ml.features import derive_features, FEATURE_COLS, CATEGORICAL_COLS

logger = logging.getLogger(__name__)


def compute_mase(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_train_history: np.ndarray,
    lag: int = 7,
) -> float:
    """Compute Mean Absolute Scaled Error against seasonal naive lag benchmark.

    mase = mean(|y_true - y_pred|) / mean(|y_train[lag:] - y_train[:-lag]|)
    """
    if len(y_true) == 0 or len(y_train_history) <= lag:
        return 1.0

    mae = np.mean(np.abs(y_true - y_pred))
    naive_diff = np.abs(y_train_history[lag:] - y_train_history[:-lag])
    scale = np.mean(naive_diff)
    if scale <= 1e-6:
        scale = 1.0

    return float(mae / scale)


def run_walk_forward_backtest(
    df: pd.DataFrame,
    commodity: str,
    n_windows: int = 5,
    horizon: int = FORECAST_HORIZON_DAYS,
) -> Dict[str, Any]:
    """Execute expanding-window walk-forward backtest.

    Splits chronologically on global calendar dates:
    Takes n_windows test cutoffs spanning the last part of the timeline,
    trains on all preceding historical data, and predicts forward 14 days.
    """
    logger.info("Starting walk-forward backtest for %s (%d windows)...", commodity, n_windows)
    comm_mandis = pooled_mandis(commodity)
    df_comm = df[(df["Commodity"] == commodity) & (df["Mandi"].isin(comm_mandis))].copy()
    df_comm["date"] = pd.to_datetime(df_comm["date"])
    df_comm = df_comm.sort_values(by=["Mandi", "date"]).reset_index(drop=True)

    # Global unique sorted dates
    unique_dates = sorted(df_comm["date"].unique())
    total_dates = len(unique_dates)
    if total_dates < 40:
        raise ValueError(f"Insufficient distinct calendar dates ({total_dates}) for {commodity}")

    # Reserve the final ~25% for walk-forward evaluation
    start_eval_idx = int(total_dates * 0.75)
    # Ensure there are at least horizon days after the cutoff
    end_eval_idx = total_dates - horizon - 1
    if end_eval_idx <= start_eval_idx:
        start_eval_idx = max(20, end_eval_idx - n_windows * 5)

    cutoff_indices = np.linspace(start_eval_idx, end_eval_idx, n_windows, dtype=int)
    cutoff_dates = [unique_dates[i] for i in cutoff_indices]

    core_mandis_list = [
        s["canonical"] for s in CORE_SERIES if s["commodity"] == commodity
    ]

    all_predictions: List[Dict[str, Any]] = []
    per_mandi_errors: Dict[str, List[float]] = {m: [] for m in comm_mandis}
    per_mandi_actuals: Dict[str, List[float]] = {m: [] for m in comm_mandis}
    per_mandi_p50s: Dict[str, List[float]] = {m: [] for m in comm_mandis}
    per_mandi_coverages: Dict[str, List[bool]] = {m: [] for m in comm_mandis}
    per_mandi_train_histories: Dict[str, List[float]] = {m: [] for m in comm_mandis}

    for cutoff_dt in cutoff_dates:
        cutoff_str = cutoff_dt.strftime("%Y-%m-%d")
        logger.info("Evaluating cutoff date: %s for %s", cutoff_str, commodity)

        # 1. Training set: strictly dates <= cutoff_dt
        df_train_raw = df_comm[df_comm["date"] <= cutoff_dt].copy()
        df_train_feat, m_map, d_map = derive_features(df_train_raw)

        # Build multi-horizon training targets
        groups_train = df_train_feat.groupby("Mandi", group_keys=False)
        for h in range(1, horizon + 1):
            df_train_feat[f"target_h_{h}"] = groups_train["ModalPrice"].shift(-h) * 100.0

        # Train models for each horizon & quantile
        window_models: Dict[Tuple[int, float], LGBMRegressor] = {}
        for h in range(1, horizon + 1):
            target_col = f"target_h_{h}"
            valid = df_train_feat[target_col].notna()
            if valid.sum() < 20:
                continue
            X_tr = df_train_feat.loc[valid, FEATURE_COLS]
            y_tr = df_train_feat.loc[valid, target_col].to_numpy()

            for alpha in QUANTILE_ALPHAS:
                reg = LGBMRegressor(
                    objective="quantile",
                    alpha=alpha,
                    num_leaves=31,
                    min_child_samples=20,
                    n_estimators=150,
                    learning_rate=0.08,
                    subsample=0.8,
                    colsample_bytree=0.8,
                    random_state=42,
                    verbosity=-1,
                    n_jobs=-1,
                )
                reg.fit(X_tr, y_tr, categorical_feature=CATEGORICAL_COLS)
                window_models[(h, alpha)] = reg

        # 2. Evaluation at cutoff_dt:
        # Full features derived up to test period
        df_eval_raw = df_comm.copy()
        df_eval_feat, _, _ = derive_features(df_eval_raw, mandi_mapping=m_map, district_mapping=d_map)

        for mandi in comm_mandis:
            # Find the exact row for this mandi on or immediately before cutoff_dt
            mandi_hist = df_eval_feat[
                (df_eval_feat["Mandi"] == mandi) & (df_eval_feat["date"] <= cutoff_dt)
            ]
            if len(mandi_hist) == 0:
                continue
            X_eval = mandi_hist.iloc[[-1]][FEATURE_COLS].copy()

            # Save training price history in paise for MASE scaling
            train_prices_paise = mandi_hist["ModalPrice"].to_numpy() * 100.0
            per_mandi_train_histories[mandi].extend(train_prices_paise.tolist())

            # Find actual subsequent prices for next 14 trading observations
            mandi_future = df_comm[
                (df_comm["Mandi"] == mandi) & (df_comm["date"] > cutoff_dt)
            ]
            if len(mandi_future) == 0:
                continue

            actual_slice = mandi_future.head(horizon)
            actual_paise = (actual_slice["ModalPrice"].to_numpy() * 100.0).round().astype(int).tolist()
            actual_dates = actual_slice["date"].dt.strftime("%Y-%m-%d").tolist()

            forecast_days = []
            band_contained = []
            m_p50s = []
            m_acts = []

            for h in range(1, len(actual_paise) + 1):
                if (h, 0.10) not in window_models or (h, 0.50) not in window_models or (h, 0.90) not in window_models:
                    continue
                p10 = int(round(window_models[(h, 0.10)].predict(X_eval)[0]))
                p50 = int(round(window_models[(h, 0.50)].predict(X_eval)[0]))
                p90 = int(round(window_models[(h, 0.90)].predict(X_eval)[0]))

                # Ensure sorted
                p10, p50, p90 = sorted((p10, p50, p90))
                act = actual_paise[h - 1]
                in_band = bool(p10 <= act <= p90)

                target_date_str = actual_dates[h - 1] if (h - 1) < len(actual_dates) else ""
                forecast_days.append({
                    "date": target_date_str,
                    "p10_paise": p10,
                    "p50_paise": p50,
                    "p90_paise": p90,
                })
                band_contained.append(in_band)
                m_p50s.append(p50)
                m_acts.append(act)

                # Append to per-mandi lists
                per_mandi_actuals[mandi].append(act)
                per_mandi_p50s[mandi].append(p50)
                per_mandi_coverages[mandi].append(in_band)

            if forecast_days:
                step_mase = compute_mase(
                    np.array(m_acts), np.array(m_p50s), np.array(per_mandi_train_histories[mandi])
                )
                step_cov_bps = int(round(np.mean(band_contained) * 10000))

                all_predictions.append({
                    "cutoff_date": cutoff_str,
                    "commodity": commodity,
                    "market": mandi,
                    "forecast": forecast_days,
                    "actual_paise": actual_paise[:len(forecast_days)],
                    "band_contained_actual": band_contained,
                    "mase_at_cutoff": round(step_mase, 4),
                    "coverage_at_cutoff_bps": step_cov_bps,
                })

    # Compute overall metrics per mandi and pooled
    mase_per_mandi: Dict[str, float] = {}
    coverage_bps_per_mandi: Dict[str, int] = {}

    all_pooled_actuals = []
    all_pooled_p50s = []
    all_pooled_coverages = []
    all_pooled_histories = []

    for mandi in comm_mandis:
        acts = np.array(per_mandi_actuals[mandi])
        p50s = np.array(per_mandi_p50s[mandi])
        covs = np.array(per_mandi_coverages[mandi])
        hists = np.array(per_mandi_train_histories[mandi])

        if len(acts) > 0:
            mase = compute_mase(acts, p50s, hists)
            cov_bps = int(round(float(np.mean(covs)) * 10000))
            mase_per_mandi[mandi] = round(mase, 3)
            coverage_bps_per_mandi[mandi] = cov_bps

            all_pooled_actuals.extend(acts.tolist())
            all_pooled_p50s.extend(p50s.tolist())
            all_pooled_coverages.extend(covs.tolist())
            all_pooled_histories.extend(hists.tolist())
        else:
            mase_per_mandi[mandi] = 1.0
            coverage_bps_per_mandi[mandi] = 8000

    pooled_mase = compute_mase(
        np.array(all_pooled_actuals),
        np.array(all_pooled_p50s),
        np.array(all_pooled_histories),
    ) if all_pooled_actuals else 1.0
    pooled_cov_bps = int(round(float(np.mean(all_pooled_coverages)) * 10000)) if all_pooled_coverages else 8000

    results = {
        "commodity": commodity,
        "pooled_mandis": comm_mandis,
        "core_mandis": core_mandis_list,
        "mase_pooled": round(pooled_mase, 3),
        "coverage_bps_pooled": pooled_cov_bps,
        "mase_per_mandi": mase_per_mandi,
        "coverage_bps_per_mandi": coverage_bps_per_mandi,
        "walkforward_points": all_predictions,
    }
    logger.info("Backtest %s results: Pooled MASE=%.3f, Pooled Coverage=%d bps",
                commodity, results["mase_pooled"], results["coverage_bps_pooled"])
    return results
