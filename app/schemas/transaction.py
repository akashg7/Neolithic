from pydantic import BaseModel, validator
from typing import Optional, Literal, List
from datetime import datetime

EscrowStatusType = Literal[
    'PENDING_BUYER_DEPOSIT',
    'DEPOSIT_HELD',
    'IN_TRANSIT',
    'ARRIVED_PENDING_INSPECTION',
    'INSPECTION_PASSED',
    'FUNDS_RELEASED',
    'DISPUTED_QUALITY',
    'DISPUTED_NO_SHOW',
    'CANCELLED_REFUNDED'
]

class CreateOrderResponse(BaseModel):
    transaction_id: str
    offer_id: str
    amount_paise: int
    razorpay_order_id: Optional[str] = None
    status: EscrowStatusType

    @validator("transaction_id", "offer_id", pre=True)
    def cast_id_to_str(cls, v):
        return str(v) if v is not None else None


class EscrowEventOut(BaseModel):
    id: str
    transaction_id: str
    status_from: Optional[EscrowStatusType] = None
    status_to: EscrowStatusType
    actor_id: str
    note: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

    @validator("id", "transaction_id", "actor_id", pre=True)
    def cast_id_to_str(cls, v):
        return str(v) if v is not None else None


class TransactionOut(BaseModel):
    id: str
    offer_id: str
    amount_paise: int
    razorpay_order_id: Optional[str] = None
    status: EscrowStatusType
    created_at: Optional[datetime] = None
    events: List[EscrowEventOut] = []

    class Config:
        from_attributes = True

    @validator("id", "offer_id", pre=True)
    def cast_id_to_str(cls, v):
        return str(v) if v is not None else None

class FSMTransitionReq(BaseModel):
    action: Literal['DEPOSIT_PAID', 'DISPATCHED', 'ARRIVED', 'INSPECTED_OK', 'INSPECTED_REJECT', 'FUNDS_TRANSFER', 'NO_SHOW', 'REFUND']
    note: Optional[str] = None
