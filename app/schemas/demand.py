from pydantic import BaseModel, Field, field_validator
from typing import Optional, Union

from app.utils.id_resolver import slug_of

class DemandCreate(BaseModel):
    commodity_id: Union[int, str]          # slug ("cmd_onion") or integer id
    quantity_qtl: int = Field(..., gt=0)
    expected_price_paise: Optional[int] = None
    market_id: Optional[Union[int, str]] = None
    warehouse_id: Optional[int] = None
    desired_grade: Optional[str] = None

class DemandOut(BaseModel):
    id: int
    commodity_id: str
    quantity_qtl: int
    expected_price_paise: Optional[int] = None
    market_id: Optional[str] = None
    warehouse_id: Optional[int] = None
    desired_grade: Optional[str] = None
    status: str
    source: Optional[str] = None

    @field_validator("commodity_id", mode="before")
    @classmethod
    def commodity_slug(cls, v): return slug_of("commodity", v)

    @field_validator("market_id", mode="before")
    @classmethod
    def market_slug(cls, v): return slug_of("market", v)

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
