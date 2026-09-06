from pydantic import BaseModel, Field, field_validator
from typing import Optional


class OtpRequestReq(BaseModel):
    phone: str = Field(..., min_length=10, max_length=15)


class OtpRequestRes(BaseModel):
    ok: bool = True
    expires_in_s: int
    dev_otp: Optional[str] = None


class OtpVerifyReq(BaseModel):
    phone: str
    code: str = Field(..., min_length=6, max_length=6)


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    phone: str = Field(..., min_length=10, max_length=15)
    code: str = Field(..., min_length=6, max_length=6)
    role: str = Field(..., pattern=r"^(FARMER|BUYER|FPO_ADMIN)$")
    locale: str = "mr"
    district_id: Optional[int] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    company_name: Optional[str] = None   # required only for role=BUYER


class UserResponse(BaseModel):
    id: str
    name: str
    phone: str
    role: str
    locale: str
    district_id: Optional[int] = None
    
    @field_validator("id", mode="before")
    def id_to_str(cls, v):
        return str(v)

    @field_validator("role", mode="before")
    def role_upper(cls, v):
        return str(v).upper() if v else v

    class Config:
        from_attributes = True


class FarmerProfileOut(BaseModel):
    fpo_id: Optional[int] = None

    class Config:
        from_attributes = True


class BuyerProfileOut(BaseModel):
    company_name: Optional[str] = None
    verified_status: bool = False
    tier: str
    gst_last4: Optional[str] = None
    deals_completed: int
    on_time_payment_bps: int
    renegotiation_bps: int

    class Config:
        from_attributes = True


class UserDetailResponse(BaseModel):
    id: str
    name: str
    phone: str
    role: str
    locale: str
    district_id: Optional[int] = None
    village: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    verified: bool
    created_at: Optional[str] = None
    farmer_profile: Optional[FarmerProfileOut] = None
    buyer_profile: Optional[BuyerProfileOut] = None

    @field_validator("id", mode="before")
    def id_to_str(cls, v):
        return str(v)

    @field_validator("role", mode="before")
    def role_upper(cls, v):
        return str(v).upper() if v else v

    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    user: UserResponse
    token: str


class LocaleUpdateRequest(BaseModel):
    locale: str
