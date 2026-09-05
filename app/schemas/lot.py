from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class LotCreate(BaseModel):
    crop: str = Field(..., min_length=1, max_length=100)
    quantity_kg: int = Field(..., gt=0)
    lat: Optional[float] = None
    lng: Optional[float] = None
    image_url: Optional[str] = None


class LotOut(BaseModel):
    id: int
    farmer_id: int
    crop: str
    quantity_kg: int
    grade: Optional[str] = None
    image_url: Optional[str] = None
    self_assay_answers: Optional[dict] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    price_min_paise_per_qtl: Optional[int] = None
    price_mid_paise_per_qtl: Optional[int] = None
    price_max_paise_per_qtl: Optional[int] = None
    status: str = "active"
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SelfAssayRequest(BaseModel):
    size_uniformity: str = Field(..., pattern=r"^(high|medium|low)$")
    color_uniformity: str = Field(..., pattern=r"^(high|medium|low)$")
    damage_percent: int = Field(..., ge=0, le=100)
    sprouting_percent: int = Field(..., ge=0, le=100)
    moisture_level: str = Field(..., pattern=r"^(dry|normal|moist)$")
    foreign_matter: str = Field(..., pattern=r"^(none|low|moderate|high)$")


class SelfAssayResponse(BaseModel):
    lot_id: int
    grade: str
    improvement_tip: str
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
    crop: str
    desired_qty_kg: int
    max_price_paise_per_qtl: Optional[int] = None
    distance_km: Optional[float] = None
    match_score: float


class LotMatchesResponse(BaseModel):
    lot_id: int
    matches: list[MatchResult]


class BatchLotMemberOut(BaseModel):
    source_lot_id: int
    quantity_contributed_kg: int

    class Config:
        from_attributes = True


class BatchLotOut(BaseModel):
    id: int
    crop: str
    quantity_kg: int
    grade: Optional[str] = None
    price_min_paise_per_qtl: Optional[int] = None
    price_mid_paise_per_qtl: Optional[int] = None
    price_max_paise_per_qtl: Optional[int] = None
    status: str
    member_lots: list[BatchLotMemberOut]

    class Config:
        from_attributes = True
