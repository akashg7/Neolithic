from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class OfferLotItem(BaseModel):
    lot_id: int
    quantity_allocated_kg: int = Field(..., gt=0)


class OfferCreate(BaseModel):
    lots: list[OfferLotItem] = Field(..., min_length=1)
    offered_price_paise_per_qtl: int = Field(..., gt=0)


class OfferLotOut(BaseModel):
    lot_id: int
    quantity_allocated_kg: int

    class Config:
        from_attributes = True


class OfferOut(BaseModel):
    id: int
    buyer_id: int
    offered_price_paise_per_qtl: int
    total_quantity_kg: int
    status: str
    lots: list[OfferLotOut] = []
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class OfferAction(BaseModel):
    action: str = Field(..., pattern=r"^(accept|reject)$")
