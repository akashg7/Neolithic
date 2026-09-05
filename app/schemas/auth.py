from pydantic import BaseModel, Field
from typing import Optional


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    phone: str = Field(..., min_length=10, max_length=15)
    password: str = Field(..., min_length=6)
    role: str = Field(..., pattern=r"^(farmer|buyer|fpo_admin)$")
    lat: Optional[float] = None
    lng: Optional[float] = None
    preferred_language: str = "en"
    company_name: Optional[str] = None   # required only for role=buyer
    fpo_id: Optional[int] = None         # optional, for farmer


class LoginRequest(BaseModel):
    phone: str
    password: str


class UserResponse(BaseModel):
    id: int
    name: str
    phone: str
    role: str
    verified: bool
    preferred_language: str

    class Config:
        from_attributes = True


class FarmerProfileOut(BaseModel):
    fpo_id: Optional[int] = None

    class Config:
        from_attributes = True


class BuyerProfileOut(BaseModel):
    company_name: Optional[str] = None
    verified_status: bool = False

    class Config:
        from_attributes = True


class UserDetailResponse(BaseModel):
    id: int
    name: str
    phone: str
    role: str
    lat: Optional[float] = None
    lng: Optional[float] = None
    preferred_language: str
    verified: bool
    created_at: Optional[str] = None
    farmer_profile: Optional[FarmerProfileOut] = None
    buyer_profile: Optional[BuyerProfileOut] = None

    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    user: UserResponse
    token: str
