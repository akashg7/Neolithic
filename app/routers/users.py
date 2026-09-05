from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.auth import UserDetailResponse, FarmerProfileOut, BuyerProfileOut

router = APIRouter()


@router.get("/me", response_model=UserDetailResponse)
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
        id=user_with_profiles.id,
        name=user_with_profiles.name,
        phone=user_with_profiles.phone,
        role=user_with_profiles.role,
        lat=user_with_profiles.lat,
        lng=user_with_profiles.lng,
        preferred_language=user_with_profiles.preferred_language,
        verified=user_with_profiles.verified,
        created_at=user_with_profiles.created_at.isoformat() if user_with_profiles.created_at else None,
        farmer_profile=FarmerProfileOut.model_validate(user_with_profiles.farmer_profile)
            if user_with_profiles.farmer_profile else None,
        buyer_profile=BuyerProfileOut.model_validate(user_with_profiles.buyer_profile)
            if user_with_profiles.buyer_profile else None,
    )
    return response
