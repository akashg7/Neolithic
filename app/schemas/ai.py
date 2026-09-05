from pydantic import BaseModel
from typing import Optional


class ForecastDay(BaseModel):
    date: str
    p10_paise: int
    p50_paise: int
    p90_paise: int
    confidence: float


class PriceForecastResponse(BaseModel):
    mandi: str
    commodity: str
    forecasts: list[ForecastDay]


class SaleWindowResponse(BaseModel):
    lot_id: int
    recommendation: str  # "SELL" | "HOLD" | "NO_ADVICE"
    expected_gain_paise: Optional[int] = None
    worst_case_paise: Optional[int] = None
    hold_until_date: Optional[str] = None
    itemised_costs: Optional[dict] = None
    reason: Optional[str] = None
