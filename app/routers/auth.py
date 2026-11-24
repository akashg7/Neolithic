"""Auth router — HTTP concerns only (parsing, status codes). Owner: Member 1.

All business logic lives in `AuthService`, injected via `Depends` (DIP).
"""
from fastapi import APIRouter, Depends, status

from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.auth import (
    AuthResponse,
    BuyerProfileOut,
    DemoLoginRequest,
    FarmerProfileOut,
    LocaleUpdateRequest,
    MeResponse,
    OtpRequestReq,
    OtpRequestRes,
    OtpVerifyReq,
    RegisterRequest,
    UserDetailResponse,
)
from app.services.auth_service import AuthService, get_auth_service

router = APIRouter()


@router.post("/otp/request", response_model=OtpRequestRes)
async def request_otp(payload: OtpRequestReq, service: AuthService = Depends(get_auth_service)):
    """Request an OTP for a phone number (max 3 per 10 minutes)."""
    return await service.request_otp(payload.phone)


@router.post("/otp/verify", response_model=AuthResponse)
async def verify_otp(payload: OtpVerifyReq, service: AuthService = Depends(get_auth_service)):
    """Verify OTP and login an existing user."""
    return await service.verify_otp(payload.phone, payload.code)


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, service: AuthService = Depends(get_auth_service)):
    """Register a new user (User + role profile via UserFactory) after verifying OTP."""
    return await service.register(payload)


@router.post("/demo-login", response_model=AuthResponse)
async def demo_login(payload: DemoLoginRequest, service: AuthService = Depends(get_auth_service)):
    """One-tap sign-in as the seeded demo farmer or buyer (DEMO_MODE only; 404 otherwise)."""
    return await service.demo_login(payload.role)


@router.get("/me", response_model=MeResponse)
async def get_me(
    user: User = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
):
    """Get the current authenticated user's profile (identity taken from the JWT)."""
    u = await service.get_profile(user.id)
    return MeResponse(user=UserDetailResponse(
        id=str(u.id),
        name=u.name,
        phone=u.phone,
        role=u.role.upper(),
        lat=u.lat,
        lng=u.lng,
        locale=u.locale,
        district_id=u.district_id,
        village=u.village,
        verified=u.verified,
        created_at=u.created_at.isoformat() if u.created_at else None,
        farmer_profile=FarmerProfileOut.model_validate(u.farmer_profile) if u.farmer_profile else None,
        buyer_profile=BuyerProfileOut.model_validate(u.buyer_profile) if u.buyer_profile else None,
    ))


@router.post("/locale")
async def update_locale(
    payload: LocaleUpdateRequest,
    user: User = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
):
    """Update the user's preferred locale."""
    await service.update_locale(user, payload.locale)
    return {"ok": True}
