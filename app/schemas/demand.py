from pydantic import BaseModel, Field
from typing import Optional

class DemandCreate(BaseModel):
    commodity_id: int
    quantity_qtl: int = Field(..., gt=0)
    expected_price_paise: Optional[int] = None
    market_id: Optional[int] = None
    warehouse_id: Optional[int] = None
    desired_grade: Optional[str] = None

class DemandOut(BaseModel):
    id: int
    commodity_id: int
    quantity_qtl: int
    expected_price_paise: Optional[int] = None
    market_id: Optional[int] = None
    warehouse_id: Optional[int] = None
    status: str

    class Config:
        from_attributes = True

class DemandMatchLot(BaseModel):
    lot_id: int
    farmer_name: Optional[str] = None
    commodity_id: int
    grade: Optional[str] = None
    available_qtl: int
    allocated_qtl: int
    expected_price_paise: Optional[int] = None
    distance_km: Optional[float] = None
    match_score: float

class DemandMatchesResponse(BaseModel):
    demand_id: int
    total_available_qtl: int
    combination: list[DemandMatchLot]
    estimated_total_cost_paise: Optional[int] = None
