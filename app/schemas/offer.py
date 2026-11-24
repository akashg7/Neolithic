from pydantic import BaseModel, Field, model_validator, field_validator
from typing import Optional, List, Literal, Any, Union
from datetime import datetime


class OfferLotItem(BaseModel):
    lot_id: str
    qty_allocated_kg: int

    class Config:
        from_attributes = True


class OfferCreate(BaseModel):
    demand_id: Optional[str] = None
    lot_ids: List[Union[int, str]] = Field(..., min_length=1)
    qty_kg: Optional[int] = None
    price_paise_per_qtl: Optional[int] = None
    offered_price_paise: Optional[int] = None

    @model_validator(mode="before")
    @classmethod
    def reconcile_price_and_qty(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Resolve price
            if "price_paise_per_qtl" not in data or data["price_paise_per_qtl"] is None:
                if "offered_price_paise" in data and data["offered_price_paise"] is not None:
                    data["price_paise_per_qtl"] = data["offered_price_paise"]
                else:
                    data["price_paise_per_qtl"] = 200000  # Default fallback price
            # Resolve qty
            if "qty_kg" not in data or data["qty_kg"] is None:
                data["qty_kg"] = 1000  # Default 10 qtl = 1000 kg
        return data


class OfferCounterReq(BaseModel):
    price_paise_per_qtl: Optional[int] = None
    counter_price_paise: Optional[int] = None
    note: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def reconcile_counter_price(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "price_paise_per_qtl" not in data or data["price_paise_per_qtl"] is None:
                if "counter_price_paise" in data and data["counter_price_paise"] is not None:
                    data["price_paise_per_qtl"] = data["counter_price_paise"]
                else:
                    data["price_paise_per_qtl"] = 200000
        return data


class OfferDto(BaseModel):
    id: str
    demand_id: Optional[str] = None
    buyer_id: str
    farmer_id: Optional[str] = None
    pool_id: Optional[str] = None
    price_paise_per_qtl: int
    offered_price_paise: Optional[int] = None
    qty_kg: int
    round: int
    parent_offer_id: Optional[str] = None
    initiator: Literal['BUYER', 'FARMER']
    status: Literal['OPEN', 'ACCEPTED', 'REJECTED', 'COUNTERED', 'EXPIRED', 'WITHDRAWN']
    expires_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    lots: List[OfferLotItem] = []
    note: Optional[str] = None
    tx_id: Optional[str] = None  # set once the offer is ACCEPTED and escrow exists

    class Config:
        from_attributes = True

    @field_validator("id", "demand_id", "buyer_id", "farmer_id", "pool_id", "parent_offer_id", mode="before")
    @classmethod
    def cast_id_to_str(cls, v: Any) -> Optional[str]:
        return str(v) if v is not None else None

    @model_validator(mode="before")
    @classmethod
    def populate_offered_price(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "offered_price_paise" not in data or data["offered_price_paise"] is None:
                data["offered_price_paise"] = data.get("price_paise_per_qtl")
        elif hasattr(data, "price_paise_per_qtl"):
            pass
        return data


OfferOut = OfferDto
