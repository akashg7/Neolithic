"""
Feature Engineering Pipeline (Person A)

Re-derives all features strictly backward-looking from clean
`ModalPrice`, `Arrivals`, and `date` with ZERO future leakage:
- Lags [1, 2, 3, 7, 14, 21, 28] on price
- Rolling [7, 14, 30] mean/std/min/max (all on .shift(1))
- Momentum: shift(1) - shift(8), shift(1) - shift(15)
- Spread = max - min (shifted)
- Arrivals: arr_lag_1, arr_roll_mean_7, arr_ratio
- Calendar: month_sin/cos, doy_sin/cos
- Weather: rain_anomaly, temp_anomaly (backward-looking 30-day mean deviation)
- Pooling: mandi_id (category), district_id (category), lat, lon, lat_sin/cos, lon_sin/cos
"""

from __future__ import annotations

from typing import Tuple, List, Dict, Any
import numpy as np
import pandas as pd


FEATURE_COLS: List[str] = [
    # Price lags
    "modal_lag_1",
    "modal_lag_2",
    "modal_lag_3",
    "modal_lag_7",
    "modal_lag_14",
    "modal_lag_21",
    "modal_lag_28",
    # Rolling stats (strictly shifted)
    "rolling_mean_7",
    "rolling_std_7",
    "rolling_min_7",
    "rolling_max_7",
    "rolling_mean_14",
    "rolling_std_14",
    "rolling_min_14",
    "rolling_max_14",
    "rolling_mean_30",
    "rolling_std_30",
    "rolling_min_30",
    "rolling_max_30",
    # Price momentum & spread
    "momentum_7",
    "momentum_14",
    "price_spread_7",
    "price_spread_30",
    # Arrivals dynamics
    "arr_lag_1",
    "arr_roll_mean_7",
    "arr_ratio",
    # Calendar features
    "month_sin",
    "month_cos",
    "doy_sin",
    "doy_cos",
    # Backward-looking weather anomalies
    "temp_anomaly_backward",
    "rain_anomaly_backward",
    # Geolocation & spatial coordinates
    "lat",
    "lon",
    "lat_sin",
    "lat_cos",
    "lon_sin",
    "lon_cos",
    # Pooling categoricals
    "mandi_id",
    "district_id",
]

CATEGORICAL_COLS: List[str] = ["mandi_id", "district_id"]


def derive_features(
    df: pd.DataFrame,
    mandi_mapping: Dict[str, int] | None = None,
    district_mapping: Dict[str, int] | None = None,
) -> Tuple[pd.DataFrame, Dict[str, int], Dict[str, int]]:
    """Derive all features for input DataFrame without any future leakage.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with columns: date, Commodity, Mandi, ModalPrice, Arrivals,
        temp_avg, rainfall, lat, lon, district_name.
    mandi_mapping : dict, optional
        Pre-fit mapping of Mandi name -> integer code.
    district_mapping : dict, optional
        Pre-fit mapping of district_name -> integer code.

    Returns
    -------
    (df_feat, mandi_mapping, district_mapping)
    """
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(by=["Commodity", "Mandi", "date"]).reset_index(drop=True)

    # 1. Categorical Encodings (Mandi and District)
    if mandi_mapping is None:
        unique_mandis = sorted(df["Mandi"].unique())
        mandi_mapping = {m: i for i, m in enumerate(unique_mandis)}
    df["mandi_id"] = df["Mandi"].map(mandi_mapping).fillna(-1).astype(int)

    if district_mapping is None:
        unique_districts = sorted(df["district_name"].unique()) if "district_name" in df.columns else []
        district_mapping = {d: i for i, d in enumerate(unique_districts)}
    if "district_name" in df.columns:
        df["district_id"] = df["district_name"].map(district_mapping).fillna(-1).astype(int)
    else:
        df["district_id"] = 0

    # 2. Calendar Features (deterministic function of date)
    month = df["date"].dt.month
    doy = df["date"].dt.dayofyear
    df["month_sin"] = np.sin(2 * np.pi * month / 12.0)
    df["month_cos"] = np.cos(2 * np.pi * month / 12.0)
    df["doy_sin"] = np.sin(2 * np.pi * doy / 365.25)
    df["doy_cos"] = np.cos(2 * np.pi * doy / 365.25)

    # 3. Geolocation & Spatial Features
    lat = df["lat"].astype(float)
    lon = df["lon"].astype(float)
    lat_rad = np.radians(lat)
    lon_rad = np.radians(lon)
    df["lat_sin"] = np.sin(lat_rad)
    df["lat_cos"] = np.cos(lat_rad)
    df["lon_sin"] = np.sin(lon_rad)
    df["lon_cos"] = np.cos(lon_rad)

    # 4. Grouped Features (strictly backward-looking per (Commodity, Mandi))
    groups = df.groupby(["Commodity", "Mandi"], group_keys=False)

    # Price lags
    p = groups["ModalPrice"]
    df["modal_lag_1"] = p.shift(1)
    df["modal_lag_2"] = p.shift(2)
    df["modal_lag_3"] = p.shift(3)
    df["modal_lag_7"] = p.shift(7)
    df["modal_lag_14"] = p.shift(14)
    df["modal_lag_21"] = p.shift(21)
    df["modal_lag_28"] = p.shift(28)

    # Rolling price statistics on shifted price (.shift(1))
    p_shift1 = p.shift(1)
    for w in (7, 14, 30):
        roll = p_shift1.rolling(w, min_periods=1)
        df[f"rolling_mean_{w}"] = roll.mean()
        df[f"rolling_std_{w}"] = roll.std().fillna(0.0)
        df[f"rolling_min_{w}"] = roll.min()
        df[f"rolling_max_{w}"] = roll.max()

    # Momentum & Spread
    df["momentum_7"] = p.shift(1) - p.shift(8)
    df["momentum_14"] = p.shift(1) - p.shift(15)
    df["price_spread_7"] = df["rolling_max_7"] - df["rolling_min_7"]
    df["price_spread_30"] = df["rolling_max_30"] - df["rolling_min_30"]

    # Arrivals features
    arr = groups["Arrivals"]
    arr_shift1 = arr.shift(1)
    df["arr_lag_1"] = arr_shift1
    df["arr_roll_mean_7"] = arr_shift1.rolling(7, min_periods=1).mean()
    df["arr_ratio"] = df["arr_lag_1"] / (df["arr_roll_mean_7"] + 1e-6)

    # Weather anomalies (deviation from backward-looking 30-day mean of shifted weather)
    t = groups["temp_avg"]
    t_shift1 = t.shift(1)
    t_roll30 = t_shift1.rolling(30, min_periods=1).mean()
    df["temp_anomaly_backward"] = t_shift1 - t_roll30

    r = groups["rainfall"]
    r_shift1 = r.shift(1)
    r_roll30 = r_shift1.rolling(30, min_periods=1).mean()
    df["rain_anomaly_backward"] = r_shift1 - r_roll30

    # Fill initial boundary NaNs and strictly enforce dtypes (float/int)
    for col in FEATURE_COLS:
        if col in df.columns:
            df[col] = df[col].fillna(0.0)
            if col in CATEGORICAL_COLS:
                df[col] = df[col].astype(int)
            else:
                df[col] = df[col].astype(float)

    return df, mandi_mapping, district_mapping


def test_no_leakage() -> bool:
    """Verify that every rolling feature at row t is unchanged when future rows are deleted.

    Returns True if assertion passes.
    """
    n_days = 60
    dates = pd.date_range("2024-01-01", periods=n_days, freq="D")
    rng = np.random.default_rng(42)

    data = {
        "date": dates,
        "Commodity": ["Onion"] * n_days,
        "Mandi": ["Test APMC"] * n_days,
        "district_name": ["Test District"] * n_days,
        "ModalPrice": 1000.0 + np.cumsum(rng.normal(0, 10, n_days)),
        "Arrivals": 50.0 + rng.uniform(0, 20, n_days),
        "temp_avg": 25.0 + rng.normal(0, 2, n_days),
        "rainfall": rng.exponential(2, n_days),
        "lat": [19.0] * n_days,
        "lon": [74.0] * n_days,
    }
    df_full = pd.DataFrame(data)

    # 1. Derive features on the full 60-day dataset
    df_full_feat, m_map, d_map = derive_features(df_full)

    # 2. Derive features on truncated dataset (first 40 days only)
    cutoff = 40
    df_trunc = df_full.iloc[:cutoff].copy()
    df_trunc_feat, _, _ = derive_features(df_trunc, mandi_mapping=m_map, district_mapping=d_map)

    # 3. Assert exact equality on all feature columns up to cutoff
    for col in FEATURE_COLS:
        val_full = df_full_feat[col].iloc[:cutoff].to_numpy()
        val_trunc = df_trunc_feat[col].to_numpy()
        max_diff = np.max(np.abs(val_full - val_trunc))
        assert max_diff < 1e-9, f"Feature leakage detected in '{col}'! Max diff: {max_diff}"

    return True


if __name__ == "__main__":
    test_no_leakage()
    print("SUCCESS: test_no_leakage passed perfectly. Zero future leakage verified.")
