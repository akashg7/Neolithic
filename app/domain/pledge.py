"""Pledge quote — computes the loan a farmer can get against stored crop.
Returns None when the pledge is NOT worthwhile (server-enforced, I13)."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.constants import DEFAULT_LTV_BPS, DEFAULT_PLEDGE_RATE_BPS


@dataclass(frozen=True, slots=True)
class PledgeQuoteResult:
    """Pledge card — mirrors the PledgeQuote TypedDict / Pydantic model."""
    loan_paise: int
    interest_paise: int
    net_benefit_paise: int
    assessed_value_paise: int
    days: int
    ltv_bps: int
    rate_bps_annual: int
    warehouse_id: int | None
    is_wdra_registered: bool
    disclaimer: str


DISCLAIMER = (
    "This is an indicative quote. Final terms depend on warehouse inspection, "
    "crop grade verification, and lender approval. WDRA registration ensures "
    "your stored crop is insured and traceable."
)


def quote(
    assessed_value_paise: int,
    expected_gain_paise: int,
    days: int,
    ltv_bps: int = DEFAULT_LTV_BPS,
    rate_bps_annual: int = DEFAULT_PLEDGE_RATE_BPS,
    warehouse_id: int | None = None,
    is_wdra_registered: bool = True,
) -> PledgeQuoteResult | None:
    """Compute a pledge quote, or return None if not worthwhile.

    The pledge is only worthwhile when the expected gain from holding
    EXCEEDS the interest cost of the loan.  If ``expected_gain_paise <=
    interest_paise``, the farmer is better off selling now — no card.

    Parameters
    ----------
    assessed_value_paise : int  Crop value (conservative p10, grade-adjusted).
    expected_gain_paise  : int  Net gain from holding (from WindowResult).
    days                 : int  How long the crop will be stored.
    ltv_bps              : int  Loan-to-value ratio in basis points (default 70%).
    rate_bps_annual      : int  Annual interest rate in bps (default 12%).
    warehouse_id         : int  Which warehouse stores the crop.
    is_wdra_registered   : bool WDRA registration status.

    Returns
    -------
    PledgeQuoteResult | None — None means "don't show a pledge card".
    """
    if assessed_value_paise <= 0 or days <= 0:
        return None

    loan = assessed_value_paise * ltv_bps // 10_000
    interest = loan * rate_bps_annual * days // (10_000 * 365)

    # Gate: only show the card if gain > interest (I13)
    if expected_gain_paise <= interest:
        return None

    return PledgeQuoteResult(
        loan_paise=loan,
        interest_paise=interest,
        net_benefit_paise=expected_gain_paise - interest,
        assessed_value_paise=assessed_value_paise,
        days=days,
        ltv_bps=ltv_bps,
        rate_bps_annual=rate_bps_annual,
        warehouse_id=warehouse_id,
        is_wdra_registered=is_wdra_registered,
        disclaimer=DISCLAIMER,
    )
