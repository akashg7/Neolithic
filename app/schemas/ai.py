from pydantic import BaseModel, Field
from typing import Optional, Literal, Dict, Any

class ModelCard(BaseModel):
    mase: float
    coverage_80_bps: int

class PledgeQuote(BaseModel):
    provider_name: str
    ltv_percent: float
    interest_rate_bps: int
    max_amount_paise: int
    terms_url: str
    contact_phone: str
    valid_until: str

class AltMarket(BaseModel):
    market_id: str
    distance_km: float
    gross_price_paise: int
    net_price_paise: int

class WindowReq(BaseModel):
    commodity_id: Optional[str] = None
    crop: Optional[str] = None
    market_id: Optional[str] = None
    mandi: Optional[str] = None
    qty_kg: Optional[int] = None
    quantity_kg: Optional[int] = None
    grade: str = "A"
    current_price_paise: Optional[int] = None
    lot_id: Optional[str] = None
    horizon_days: int = 14

    @property
    def final_crop(self) -> str:
        return self.commodity_id or self.crop or "Onion"

    @property
    def final_mandi(self) -> str:
        return self.market_id or self.mandi or "Lasalgaon APMC"

    @property
    def final_qty(self) -> int:
        return self.qty_kg or self.quantity_kg or 5000

class WindowItemisedCosts(BaseModel):
    transport_paise_per_qtl: int = 0
    commission_paise_per_qtl: int = 0
    storage_paise_per_qtl: int = 0
    spoilage_paise_per_qtl: int = 0
    loading_paise_per_qtl: int = 0
    total_paise_per_qtl: int = 0

class WindowRes(BaseModel):
    action: Literal["SELL_NOW", "SELL_ELSEWHERE", "HOLD", "SPLIT", "NO_ADVICE"]
    recommendation: Optional[str] = None
    confidence: Literal["LOW", "MEDIUM", "HIGH"]
    band_width_bps: int
    sell_now_net_paise_per_qtl: Optional[int] = None
    hold_p50_net_paise_per_qtl: Optional[int] = None
    hold_p10_net_paise_per_qtl: Optional[int] = None
    expected_gain_paise: Optional[int] = None
    worst_case_paise: Optional[int] = None
    costs: Optional[WindowItemisedCosts] = None
    itemised_costs: Optional[WindowItemisedCosts] = None
    hold_days: Optional[int] = None
    model_card: ModelCard
    data_source: str
    pledge_quote: Optional[PledgeQuote] = None
    alt_market: Optional[AltMarket] = None
    refusal_reason: Optional[Literal["BAND_TOO_WIDE", "INSUFFICIENT_HISTORY", "STALE_DATA", "GAIN_BELOW_COST"]] = None
    explain_mr: str
    explain_en: str

    def __init__(self, **data):
        if "action" in data and "recommendation" not in data:
            data["recommendation"] = data["action"]
        elif "recommendation" in data and "action" not in data:
            data["action"] = data["recommendation"]
        if "costs" in data and "itemised_costs" not in data:
            data["itemised_costs"] = data["costs"]
        elif "itemised_costs" in data and "costs" not in data:
            data["costs"] = data["itemised_costs"]
        super().__init__(**data)

