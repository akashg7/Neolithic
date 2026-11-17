from pydantic import BaseModel, Field, model_validator
from typing import Optional, Any
from datetime import datetime


class DisputeCreate(BaseModel):
    transaction_id: int
    reason: str = Field(..., min_length=1, max_length=500)

    @model_validator(mode="before")
    @classmethod
    def reconcile_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "transaction_id" not in data and "tx_id" in data:
                data["transaction_id"] = int(data["tx_id"])
            if "reason" not in data and "description" in data:
                data["reason"] = data["description"]
        return data


class DisputeOut(BaseModel):
    id: int
    transaction_id: int
    raised_by: int
    raised_by_id: Optional[int] = None
    reason: str
    status: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

    @model_validator(mode="before")
    @classmethod
    def populate_raised_by_id(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "raised_by_id" not in data or data["raised_by_id"] is None:
                data["raised_by_id"] = data.get("raised_by")
            if "raised_by" not in data or data["raised_by"] is None:
                data["raised_by"] = data.get("raised_by_id")
        return data


class DisputeUpdate(BaseModel):
    status: str = Field(..., pattern=r"^(open|investigating|under_review|resolved|dismissed)$")
