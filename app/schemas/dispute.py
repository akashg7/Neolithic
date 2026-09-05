from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class DisputeCreate(BaseModel):
    transaction_id: int
    reason: str = Field(..., min_length=1, max_length=500)


class DisputeOut(BaseModel):
    id: int
    transaction_id: int
    raised_by: int
    reason: str
    status: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DisputeUpdate(BaseModel):
    status: str = Field(..., pattern=r"^(under_review|resolved|dismissed)$")
