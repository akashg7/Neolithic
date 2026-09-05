from pydantic import BaseModel, Field
from typing import Optional


class DemandCreate(BaseModel):
    crop: str = Field(..., min_length=1, max_length=100)
    desired_qty_kg: int = Field(..., gt=0)
    desired_grade: Optional[str] = None
    max_price_paise_per_qtl: Optional[int] = None
    lat: Optional[float] = None
    lng: Optional[float] = None


class DemandOut(BaseModel):
    id: int
    buyer_id: int
    crop: str
    desired_qty_kg: int
    desired_grade: Optional[str] = None
    max_price_paise_per_qtl: Optional[int] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    source: str = "real"

    class Config:
        from_attributes = True


class DemandMatchLot(BaseModel):
    lot_id: int
    farmer_name: Optional[str] = None
    crop: str
    grade: Optional[str] = None
    available_kg: int
    allocated_kg: int
    price_mid_paise_per_qtl: Optional[int] = None
    distance_km: Optional[float] = None
    match_score: float


class DemandMatchesResponse(BaseModel):
    demand_id: int
    total_available_kg: int
    combination: list[DemandMatchLot]
    estimated_total_cost_paise: Optional[int] = None
