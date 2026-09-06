from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime

class LotCreate(BaseModel):
    commodity_id: int
    quantity_qtl: int = Field(..., gt=0)
    expected_price_paise: int = Field(..., gt=0)
    market_id: Optional[int] = None
    warehouse_id: Optional[int] = None
    self_assay: Optional[dict] = None

class LotOut(BaseModel):
    id: int
    commodity_id: int
    quantity_qtl: int
    expected_price_paise: Optional[int] = None
    status: str
    market_id: Optional[int] = None
    warehouse_id: Optional[int] = None
    grade: Optional[str] = None
    image_url: Optional[str] = None

    class Config:
        from_attributes = True

class SelfAssayRequest(BaseModel):
    size_uniform: Literal[1, 2, 3]
    colour_uniform: Literal[1, 2, 3]
    damage_pct: int = Field(..., ge=0, le=100)
    sprouting: Literal[1, 2, 3]
    moisture_feel: Literal[1, 2, 3]
    foreign_matter: Literal[1, 2, 3]

class SelfAssayResponse(BaseModel):
    lot_id: int
    score: int
    grade: str
    weakest_dimension: str
    tip_mr: str
    tip_en: str
    self_assay_answers: dict

class PriceBand(BaseModel):
    min_paise_per_qtl: int
    mid_paise_per_qtl: int
    max_paise_per_qtl: int

class SaleWindowInfo(BaseModel):
    recommendation: str  # "SELL" | "HOLD" | "NO_ADVICE"
    expected_gain_paise: Optional[int] = None
    worst_case_paise: Optional[int] = None
    itemised_costs: Optional[dict] = None
    hold_until_date: Optional[str] = None
    reason: Optional[str] = None

class PriceSuggestionResponse(BaseModel):
    lot_id: int
    price_band: PriceBand
    sale_window: SaleWindowInfo

class MatchResult(BaseModel):
    buyer_demand_id: int
    buyer_name: Optional[str] = None
    commodity_id: int
    quantity_qtl: int
    expected_price_paise: Optional[int] = None
    distance_km: Optional[float] = None
    match_score: float

class LotMatchesResponse(BaseModel):
    lot_id: int
    matches: list[MatchResult]

class BatchLotMemberOut(BaseModel):
    source_lot_id: int
    quantity_contributed_qtl: int

    class Config:
        from_attributes = True

class BatchLotOut(BaseModel):
    id: int
    commodity_id: int
    quantity_qtl: int
    grade: Optional[str] = None
    expected_price_paise: Optional[int] = None
    status: str
    member_lots: list[BatchLotMemberOut]

    class Config:
        from_attributes = True
