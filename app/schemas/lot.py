from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, Literal, Any
from datetime import datetime

class LotCreate(BaseModel):
    commodity_id: str
    qty_kg: int = Field(..., gt=0)
    expected_price_paise: int = Field(..., gt=0)
    market_id: Optional[str] = None
    warehouse_id: Optional[str] = None
    self_assay: Optional[dict] = None

class LotOut(BaseModel):
    id: str
    commodity_id: str
    qty_kg: int
    expected_price_paise: Optional[int] = None
    status: Literal["DRAFT", "LISTED", "IN_AUCTION", "SOLD", "CANCELLED", "COMPLETED"]
    market_id: Optional[str] = None
    warehouse_id: Optional[str] = None
    grade: Literal["UNGRADED", "A", "B", "C", "REJECTED"]
    photo_path: Optional[str] = None
    farmer_id: str
    harvest_date: Optional[str] = None
    created_at: Optional[str] = None

    @model_validator(mode="before")
    def map_db_fields(cls, values: Any) -> Any:
        if hasattr(values, "quantity_qtl"):
            db_status = str(values.status).upper() if values.status else "DRAFT"
            if db_status == "ACTIVE":
                db_status = "LISTED"
            return {
                "id": str(values.id),
                "commodity_id": str(values.commodity_id),
                "qty_kg": values.quantity_qtl * 100,
                "expected_price_paise": values.expected_price_paise,
                "status": db_status,
                "market_id": str(values.market_id) if values.market_id else None,
                "warehouse_id": str(values.warehouse_id) if values.warehouse_id else None,
                "grade": str(values.grade) if values.grade else "UNGRADED",
                "photo_path": values.image_url,
                "farmer_id": str(values.farmer_id),
                "harvest_date": None,
                "created_at": values.created_at.isoformat() if values.created_at else None
            }
        return values

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
    lot_id: str
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
    lot_id: str
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
    lot_id: str
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
