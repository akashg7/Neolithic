"""Cost computation — all values in integer paise.  Five lines sum to total."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.constants import (
    COMMISSION_RATE_BPS,
    LOADING_PAISE_PER_KG,
    SPOILAGE_BPS_PER_DAY,
    STORAGE_PAISE_PER_KG_PER_DAY,
    TRANSPORT_PAISE_PER_KM,
)


@dataclass(frozen=True, slots=True)
class CostBreakdown:
    """Itemised holding/selling costs.  ``transport + commission + loading +
    storage + spoilage == total`` — always, by construction."""
    transport_paise: int
    commission_paise: int
    loading_paise: int
    storage_paise: int
    spoilage_paise: int
    total_paise: int


def compute_costs(
    price_paise_per_qtl: int,
    quantity_kg: int,
    distance_km: float,
    days: int,
) -> CostBreakdown:
    """Compute itemised costs for holding *days* then selling.

    Parameters
    ----------
    price_paise_per_qtl : int   Expected sale price (p50 or current spot).
    quantity_kg           : int   Lot weight.
    distance_km           : float Transport distance.
    days                  : int   0 = sell today, 1..14 = hold N days.

    Returns
    -------
    CostBreakdown with integer paise; five lines sum to total exactly.
    """
    qty_qtl = quantity_kg // 100  # 1 quintal = 100 kg

    transport = int(distance_km * TRANSPORT_PAISE_PER_KM)
    commission = price_paise_per_qtl * qty_qtl * COMMISSION_RATE_BPS // 10_000
    loading = quantity_kg * LOADING_PAISE_PER_KG
    storage = quantity_kg * days * STORAGE_PAISE_PER_KG_PER_DAY
    spoilage = price_paise_per_qtl * qty_qtl * SPOILAGE_BPS_PER_DAY * days // 10_000

    total = transport + commission + loading + storage + spoilage

    return CostBreakdown(
        transport_paise=transport,
        commission_paise=commission,
        loading_paise=loading,
        storage_paise=storage,
        spoilage_paise=spoilage,
        total_paise=total,
    )
