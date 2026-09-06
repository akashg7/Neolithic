from pydantic import BaseModel, Field, validator
from typing import Optional, List, Literal
from datetime import datetime

class OfferLotItem(BaseModel):
    lot_id: str
    qty_allocated_kg: int

    class Config:
        from_attributes = True

class OfferCreate(BaseModel):
    demand_id: Optional[str] = None
    lot_ids: List[str] = Field(..., min_length=1)
    qty_kg: int = Field(..., gt=0)
    price_paise_per_qtl: int = Field(..., gt=0)

class OfferCounterReq(BaseModel):
    price_paise_per_qtl: int = Field(..., gt=0)
    note: Optional[str] = None

class OfferDto(BaseModel):
    id: str
    demand_id: Optional[str] = None
    buyer_id: str
    farmer_id: Optional[str] = None
    pool_id: Optional[str] = None
    price_paise_per_qtl: int
    qty_kg: int
    round: int
    parent_offer_id: Optional[str] = None
    initiator: Literal['BUYER', 'FARMER']
    status: Literal['OPEN', 'ACCEPTED', 'REJECTED', 'COUNTERED', 'EXPIRED', 'WITHDRAWN']
    expires_at: Optional[datetime] = None
    created_at: datetime
    lots: List[OfferLotItem] = []
    note: Optional[str] = None

    class Config:
        from_attributes = True

    @validator("id", "demand_id", "buyer_id", "farmer_id", "pool_id", "parent_offer_id", pre=True)
    def cast_id_to_str(cls, v):
        return str(v) if v is not None else None
