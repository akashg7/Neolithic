from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.auth import (
    RegisterRequest, AuthResponse, OtpRequestReq, OtpRequestRes, 
    OtpVerifyReq, UserDetailResponse, FarmerProfileOut, BuyerProfileOut,
    LocaleUpdateRequest, MeResponse
)
from app.services import auth_service

router = APIRouter()


@router.post("/otp/request", response_model=OtpRequestRes)
async def request_otp(payload: OtpRequestReq, db: AsyncSession = Depends(get_db)):
    """Request an OTP for a phone number."""
    return await auth_service.request_otp(db, payload.phone)


@router.post("/otp/verify", response_model=AuthResponse)
async def verify_otp(payload: OtpVerifyReq, db: AsyncSession = Depends(get_db)):
    """Verify OTP and login an existing user."""
    return await auth_service.verify_otp(db, payload.phone, payload.code)


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user after verifying OTP."""
    return await auth_service.register_user(db, payload)


@router.get("/me", response_model=MeResponse)
async def get_me(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current authenticated user's profile."""
    # Reload user with relationships
    result = await db.execute(
        select(User)
        .options(selectinload(User.farmer_profile), selectinload(User.buyer_profile))
        .where(User.id == user.id)
    )
    user_with_profiles = result.scalar_one()

    response = UserDetailResponse(
        id=str(user_with_profiles.id),
        name=user_with_profiles.name,
        phone=user_with_profiles.phone,
        role=user_with_profiles.role.upper(),
        lat=user_with_profiles.lat,
        lng=user_with_profiles.lng,
        locale=user_with_profiles.locale,
        district_id=user_with_profiles.district_id,
        village=user_with_profiles.village,
        verified=user_with_profiles.verified,
        created_at=user_with_profiles.created_at.isoformat() if user_with_profiles.created_at else None,
        farmer_profile=FarmerProfileOut.model_validate(user_with_profiles.farmer_profile)
            if user_with_profiles.farmer_profile else None,
        buyer_profile=BuyerProfileOut.model_validate(user_with_profiles.buyer_profile)
            if user_with_profiles.buyer_profile else None,
    )
    return MeResponse(user=response)


@router.post("/locale")
async def update_locale(
    payload: LocaleUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update the user's preferred locale."""
    user.locale = payload.locale
    db.add(user)
    await db.commit()
    return {"ok": True}
