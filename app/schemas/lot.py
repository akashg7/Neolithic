from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, Literal, Any
from datetime import datetime

from app.utils.id_resolver import slug_of

class LotCreate(BaseModel):
    commodity_id: str
    qty_kg: Optional[int] = None
    quantity_qtl: Optional[int] = None
    # Optional: the app creates the lot at S19 and sets the price at S22 (publish).
    expected_price_paise: Optional[int] = Field(None, gt=0)
    market_id: Optional[str] = None
    warehouse_id: Optional[str] = None
    self_assay: Optional[dict] = None
    harvest_date: Optional[str] = None
    photo_path: Optional[str] = None


class LotPublishRequest(BaseModel):
    expected_price_paise: int = Field(..., gt=0, description="Asking price, paise per quintal")


class LotOut(BaseModel):
    id: str
    commodity_id: str
    qty_kg: int
    expected_price_paise: Optional[int] = None
    status: Literal["DRAFT", "LISTED", "OFFERED", "POOLED", "IN_AUCTION", "SOLD", "CANCELLED", "COMPLETED"]
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
            # DB lifecycle names (app/domain/lot_lifecycle.py) -> API enum
            db_status = {"ACTIVE": "LISTED", "LOCKED": "OFFERED"}.get(db_status, db_status)
            return {
                "id": str(values.id),
                "commodity_id": slug_of("commodity", values.commodity_id),
                "qty_kg": values.quantity_qtl * 100,
                "expected_price_paise": values.expected_price_paise,
                "status": db_status,
                "market_id": slug_of("market", values.market_id) if values.market_id else None,
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

class AssayRecordOut(BaseModel):
    """The stored self-assay of a lot, with the grade derived from it (S20)."""
    lot_id: str
    size_uniform: int
    colour_uniform: int
    sprouting: int
    damage_pct: int
    moisture_feel: int
    foreign_matter: int
    score: int
    grade: str
    weakest_dimension: str
    tip_mr: str
    tip_en: str
    photo_path: Optional[str] = None
    created_at: Optional[str] = None


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

    @field_validator("lot_id", mode="before")
    def id_to_str(cls, v):
        return str(v) if v is not None else v


class PriceBand(BaseModel):
    min_paise_per_qtl: int
    mid_paise_per_qtl: int
    max_paise_per_qtl: int
    band_source: Optional[str] = None  # AGMARKNET_SOTA | AGMARKNET_ML | SYNTHETIC | NONE

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
    market_id: Optional[str] = None     # the mandi the band/window were computed for
    market_slug: Optional[str] = None

    @field_validator("lot_id", mode="before")
    def id_to_str(cls, v):
        return str(v) if v is not None else v

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

    @field_validator("lot_id", mode="before")
    def id_to_str(cls, v):
        return str(v) if v is not None else v

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


# ── Pranay: measured-parameter grading (POST /lots/{id}/grade) ─────────────

class GradeRequest(BaseModel):
    """Measured quality parameters, all in percent (0-100).

    Which ones are required depends on the crop: onion needs moisture +
    size uniformity, grains need moisture + foreign matter, fresh vegetables
    need damage + size uniformity. The response says which rules were used.
    """
    moisture_pct: Optional[float] = Field(None, ge=0, le=100)
    foreign_matter_pct: Optional[float] = Field(None, ge=0, le=100)
    size_uniformity_pct: Optional[float] = Field(None, ge=0, le=100)
    damage_pct: Optional[float] = Field(None, ge=0, le=100)
    discoloration_pct: Optional[float] = Field(None, ge=0, le=100)


class GradeResultOut(BaseModel):
    lot_id: str
    commodity: Optional[str] = None
    strategy: str
    grade: Literal["A", "B", "C"]
    assessed_multiplier: float
    assessed_price_paise_per_qtl: Optional[int] = None
    assessed_value_paise: Optional[int] = None
    advice: list[str]


class PoolRequest(BaseModel):
    lot_ids: list[int] = Field(..., min_length=2)
    fpo_id: Optional[int] = None  # optional; must match the caller's own FPO
