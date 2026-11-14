from pydantic import BaseModel, field_validator
from typing import Optional


class UserOut(BaseModel):
    id: int
    name: str
    phone: str
    role: str
    lat: Optional[float] = None
    lng: Optional[float] = None
    preferred_language: str = "en"
    verified: bool = False

    class Config:
        from_attributes = True


class FarmerOut(BaseModel):
    """A farmer as seen by their FPO admin (`GET /api/v1/fpo/farmers`)."""
    user_id: str
    name: str
    phone: str
    district_id: Optional[str] = None
    village: Optional[str] = None
    fpo_id: Optional[str] = None
    verified: bool = False

    @field_validator("user_id", "district_id", "fpo_id", mode="before")
    def id_to_str(cls, v):
        return str(v) if v is not None else v
