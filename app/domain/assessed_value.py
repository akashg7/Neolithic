"""Assessed crop value for pledge — conservative (uses p10, not p50)."""

from __future__ import annotations

# Grade multipliers applied as integer basis-points.
# "A" = best quality, full price.  "B"/"C" = discounted.
GRADE_BPS: dict[str, int] = {
    "A": 10_000,  # 100%
    "B": 8_500,   # 85%
    "C": 7_000,   # 70%
}


def assessed_value(
    grade: str,
    quantity_kg: int,
    forecast_p10_paise_per_qtl: int,
) -> int:
    """Crop's pledge value in integer paise.

    Uses the p10 (conservative) forecast so the loan is never inflated.

    Parameters
    ----------
    grade                    : str  "A", "B", or "C".
    quantity_kg              : int  Lot weight in kg.
    forecast_p10_paise_per_qtl : int  Model's p10 estimate for this mandi/commodity.

    Returns
    -------
    int  Value in paise.

    Raises
    ------
    ValueError  If grade is not A/B/C or quantity is non-positive.
    """
    grade = grade.strip().upper()
    if grade not in GRADE_BPS:
        raise ValueError(f"Invalid grade: {grade!r} (expected A, B, or C)")
    if quantity_kg <= 0:
        raise ValueError(f"quantity_kg must be positive, got {quantity_kg}")

    qty_qtl = quantity_kg // 100
    bps = GRADE_BPS[grade]
    return forecast_p10_paise_per_qtl * qty_qtl * bps // 10_000
