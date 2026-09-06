"""Domain constants — env-overridable with sane defaults."""

import os

# ── Forecasting / decision thresholds ──────────────────────────────────
NO_ADVICE_BAND_BPS: int = int(os.getenv("NO_ADVICE_BAND_BPS", "3500"))  # 35%
MIN_HISTORY_ROWS: int = int(os.getenv("MIN_HISTORY_ROWS", "180"))
MAX_STALENESS_DAYS: int = int(os.getenv("MAX_STALENESS_DAYS", "10"))
MIN_GAIN_PAISE: int = int(os.getenv("MIN_GAIN_PAISE", "5000"))          # ₹50
FORECAST_HORIZON_DAYS: int = int(os.getenv("FORECAST_HORIZON_DAYS", "14"))

# ── Pledge defaults ────────────────────────────────────────────────────
DEFAULT_LTV_BPS: int = int(os.getenv("DEFAULT_LTV_BPS", "7000"))        # 70%
DEFAULT_PLEDGE_RATE_BPS: int = int(os.getenv("DEFAULT_PLEDGE_RATE_BPS", "1200"))  # 12% p.a.

# ── Commission / transport / storage ───────────────────────────────────
COMMISSION_RATE_BPS: int = int(os.getenv("COMMISSION_RATE_BPS", "250"))  # 2.5%
TRANSPORT_PAISE_PER_KM: int = int(os.getenv("TRANSPORT_PAISE_PER_KM", "50"))
LOADING_PAISE_PER_KG: int = int(os.getenv("LOADING_PAISE_PER_KG", "2"))
STORAGE_PAISE_PER_KG_PER_DAY: int = int(os.getenv("STORAGE_PAISE_PER_KG_PER_DAY", "5"))
SPOILAGE_BPS_PER_DAY: int = int(os.getenv("SPOILAGE_BPS_PER_DAY", "20"))  # 0.20%/day
