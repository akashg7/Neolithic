from fastapi import HTTPException, status
import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import create_access_token
from app.models.user import User, Farmer, Buyer
from app.schemas.auth import RegisterRequest, LoginRequest, AuthResponse, UserResponse


async def register_user(db: AsyncSession, payload: RegisterRequest) -> AuthResponse:
    """Register a new user. Creates User + role-specific profile (Farmer or Buyer)."""
    # Check phone uniqueness
    result = await db.execute(select(User).where(User.phone == payload.phone))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Phone number already registered"
        )

    # Create user
    user = User(
        name=payload.name,
        phone=payload.phone,
        password_hash=bcrypt.hashpw(payload.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
        role=payload.role,
        lat=payload.lat,
        lng=payload.lng,
        preferred_language=payload.preferred_language,
    )
    db.add(user)
    await db.flush()  # Get the generated user.id

    # Create role-specific profile
    if payload.role == "farmer":
        farmer = Farmer(user_id=user.id, fpo_id=payload.fpo_id)
        db.add(farmer)
    elif payload.role == "buyer":
        buyer = Buyer(user_id=user.id, company_name=payload.company_name)
        db.add(buyer)
    elif payload.role == "fpo_admin":
        # FPO admins also get a farmer profile (they are farmers who manage an FPO)
        farmer = Farmer(user_id=user.id, fpo_id=payload.fpo_id)
        db.add(farmer)

    await db.flush()

    # Generate token
    token = create_access_token({"user_id": user.id, "role": user.role})

    return AuthResponse(
        user=UserResponse.model_validate(user),
        token=token,
    )


async def login_user(db: AsyncSession, payload: LoginRequest) -> AuthResponse:
    """Authenticate user by phone + password."""
    result = await db.execute(select(User).where(User.phone == payload.phone))
    user = result.scalar_one_or_none()

    if user is None or not bcrypt.checkpw(payload.password.encode('utf-8'), user.password_hash.encode('utf-8')):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    token = create_access_token({"user_id": user.id, "role": user.role})

    return AuthResponse(
        user=UserResponse.model_validate(user),
        token=token,
    )
