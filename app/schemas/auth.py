from pydantic import BaseModel, Field, field_validator, AliasChoices
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
    district_id: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = Field(default=None, validation_alias=AliasChoices("lng", "lon"))
    village: Optional[str] = Field(None, max_length=200)   # farmer's village
    company_name: Optional[str] = None   # required only for role=BUYER


class UserResponse(BaseModel):
    id: str
    name: str
    phone: str
    role: str
    locale: str
    district_id: Optional[str] = None
    
    @field_validator("id", "district_id", mode="before")
    def id_to_str(cls, v):
        return str(v) if v is not None else v

    @field_validator("role", mode="before")
    def role_upper(cls, v):
        return str(v).upper() if v else v

    class Config:
        from_attributes = True


class FarmerProfileOut(BaseModel):
    fpo_id: Optional[str] = None

    @field_validator("fpo_id", mode="before")
    def id_to_str(cls, v):
        return str(v) if v is not None else v

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
    district_id: Optional[str] = None
    village: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = Field(default=None, validation_alias=AliasChoices("lng", "lon"))
    verified: bool
    created_at: Optional[str] = None
    farmer_profile: Optional[FarmerProfileOut] = None
    buyer_profile: Optional[BuyerProfileOut] = None

    @field_validator("id", "district_id", mode="before")
    def id_to_str(cls, v):
        return str(v) if v is not None else v

    @field_validator("role", mode="before")
    def role_upper(cls, v):
        return str(v).upper() if v else v

    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    user: UserResponse
    token: str
    access_token: Optional[str] = None
    token_type: str = "bearer"

    def __init__(self, **data):
        if "token" in data and "access_token" not in data:
            data["access_token"] = data["token"]
        elif "access_token" in data and "token" not in data:
            data["token"] = data["access_token"]
        super().__init__(**data)



class MeResponse(BaseModel):
    user: UserDetailResponse


class LocaleUpdateRequest(BaseModel):
    locale: str
