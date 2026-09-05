from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class CreateOrderResponse(BaseModel):
    transaction_id: int
    offer_id: int
    amount_paise: int
    razorpay_order_id: Optional[str] = None
    payment_status: str


class TransactionEventOut(BaseModel):
    event_type: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TransactionOut(BaseModel):
    id: int
    offer_id: int
    amount_paise: int
    razorpay_order_id: Optional[str] = None
    payment_status: str
    created_at: Optional[datetime] = None
    events: list[TransactionEventOut] = []

    class Config:
        from_attributes = True
