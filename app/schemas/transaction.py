from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, Literal, List, Any
from datetime import datetime

EscrowStatusType = str


class CreateOrderResponse(BaseModel):
    transaction_id: str
    offer_id: str
    amount_paise: int
    razorpay_order_id: Optional[str] = None
    status: EscrowStatusType

    @field_validator("transaction_id", "offer_id", mode="before")
    @classmethod
    def cast_id_to_str(cls, v: Any) -> Optional[str]:
        return str(v) if v is not None else None


class EscrowEventOut(BaseModel):
    id: str
    transaction_id: str
    status_from: Optional[str] = None
    from_state: Optional[str] = None
    status_to: str
    to_state: Optional[str] = None
    actor_id: str
    triggered_by_user_id: Optional[str] = None
    note: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

    @field_validator("id", "transaction_id", "actor_id", "triggered_by_user_id", mode="before")
    @classmethod
    def cast_id_to_str(cls, v: Any) -> Optional[str]:
        return str(v) if v is not None else None

    @model_validator(mode="before")
    @classmethod
    def reconcile_state_names(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if not data.get("from_state"):
                data["from_state"] = data.get("status_from")
            if not data.get("status_from"):
                data["status_from"] = data.get("from_state")
            if not data.get("to_state"):
                data["to_state"] = data.get("status_to")
            if not data.get("status_to"):
                data["status_to"] = data.get("to_state")
            if not data.get("triggered_by_user_id"):
                data["triggered_by_user_id"] = str(data.get("actor_id")) if data.get("actor_id") is not None else None
        elif hasattr(data, "status_from"):
            pass
        return data


class TransactionOut(BaseModel):
    id: str
    offer_id: str
    buyer_id: Optional[str] = None
    farmer_id: Optional[str] = None
    amount_paise: int
    total_amount_paise: Optional[int] = None
    razorpay_order_id: Optional[str] = None
    status: EscrowStatusType
    created_at: Optional[datetime] = None
    events: List[EscrowEventOut] = []

    class Config:
        from_attributes = True

    @field_validator("id", "offer_id", "buyer_id", "farmer_id", mode="before")
    @classmethod
    def cast_id_to_str(cls, v: Any) -> Optional[str]:
        return str(v) if v is not None else None

    @model_validator(mode="before")
    @classmethod
    def reconcile_amounts(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "total_amount_paise" not in data or data["total_amount_paise"] is None:
                data["total_amount_paise"] = data.get("amount_paise")
            if "amount_paise" not in data or data["amount_paise"] is None:
                data["amount_paise"] = data.get("total_amount_paise")
        return data


class FSMTransitionReq(BaseModel):
    action: str
    note: Optional[str] = None


class DepositReq(BaseModel):
    payment_proof: Optional[str] = None
    note: Optional[str] = None


class DispatchReq(BaseModel):
    vehicle_number: Optional[str] = None
    note: Optional[str] = None


class InspectReq(BaseModel):
    quality_confirmed: Optional[bool] = True
    note: Optional[str] = None


class ReleaseReq(BaseModel):
    note: Optional[str] = None
