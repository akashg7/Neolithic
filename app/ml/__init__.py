"""
Forecasting package — LightGBM quantile regression, pooled by commodity.

Phase 0 contract freeze. Do not edit signatures without both-person agreement.
"""

from datetime import date
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────
PKG_DIR = Path(__file__).resolve().parent
SNAPSHOT_DIR = PKG_DIR / "snapshots"
ARTIFACT_DIR = PKG_DIR / "artifacts"

# ── Core demo series (Phase 1 aliases against the CSV; exact names TBD) ──
# Each entry: (canonical_name, commodity, pooling_neighbors)
# pooling_neighbors = other mandis whose rows are pooled into this commodity's model.
CORE_SERIES = [
    # Onion
    {"canonical": "Lasalgaon APMC",   "commodity": "Onion",   "neighbors": ["Pimpalgaon APMC", "Pune(Manjri) APMC"]},
    {"canonical": "Pimpalgaon APMC",  "commodity": "Onion",   "neighbors": ["Lasalgaon APMC", "Pune(Manjri) APMC"]},
    {"canonical": "Pune(Manjri) APMC","commodity": "Onion",   "neighbors": ["Lasalgaon APMC", "Pimpalgaon APMC"]},
    # Soyabean
    {"canonical": "Latur APMC",       "commodity": "Soyabean","neighbors": ["Nanded APMC", "Akola APMC"]},
    {"canonical": "Nanded APMC",      "commodity": "Soyabean","neighbors": ["Latur APMC", "Akola APMC"]},
    {"canonical": "Akola APMC",       "commodity": "Soyabean","neighbors": ["Latur APMC", "Nanded APMC"]},
]

# Commodities to train (derived from CORE_SERIES; one pooled model per commodity).
COMMODITIES = sorted({s["commodity"] for s in CORE_SERIES})

# Full pooled mandi set per commodity (core + neighbors, deduped).
def pooled_mandis(commodity: str) -> list[str]:
    """Return the full set of mandis pooled into *commodity*'s model."""
    names: set[str] = set()
    for s in CORE_SERIES:
        if s["commodity"] == commodity:
            names.add(s["canonical"])
            names.update(s["neighbors"])
    return sorted(names)


# ── Forecast constants (also mirrored in app/domain/constants.py) ──────
FORECAST_HORIZON_DAYS = 14
QUANTILE_ALPHAS = (0.10, 0.50, 0.90)
MIN_HISTORY_ROWS = 180
MAX_STALENESS_DAYS = 10
