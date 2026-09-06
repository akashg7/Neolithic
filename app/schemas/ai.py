from pydantic import BaseModel, Field
from typing import Optional, Literal, Dict, Any

class ModelCard(BaseModel):
    mase: float
    coverage_80_bps: int

class WindowReq(BaseModel):
    commodity_id: str
    market_id: str
    qty_kg: int
    grade: str
    lot_id: Optional[str] = None
    horizon_days: int = 14

class WindowItemisedCosts(BaseModel):
    transport_paise_per_qtl: int = 0
    commission_paise_per_qtl: int = 0
    storage_paise_per_qtl: int = 0
    spoilage_paise_per_qtl: int = 0
    loading_paise_per_qtl: int = 0
    total_paise_per_qtl: int = 0

class WindowRes(BaseModel):
    recommendation: Literal["SELL_NOW", "SELL_ELSEWHERE", "HOLD", "SPLIT", "NO_ADVICE"]
    confidence: Literal["LOW", "MEDIUM", "HIGH"]
    band_width_bps: int
    sell_now_net_paise_per_qtl: int
    hold_p50_net_paise_per_qtl: int
    hold_p10_net_paise_per_qtl: int
    expected_gain_paise: int
    worst_case_paise: int
    itemised_costs: WindowItemisedCosts
    hold_days: Optional[int] = None
    model_card: ModelCard
    data_source: str
    pledge_quote: Optional[int] = None
    alt_market: Optional[str] = None
    refusal_reason: Optional[Literal["BAND_TOO_WIDE", "INSUFFICIENT_HISTORY", "STALE_DATA", "GAIN_BELOW_COST"]] = None
    explain_mr: Optional[str] = None
    explain_en: Optional[str] = None
