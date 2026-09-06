import secrets
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
import bcrypt
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies.auth import create_access_token
from app.models.user import User, Farmer, Buyer
from app.models.otp import OtpCode
from app.schemas.auth import RegisterRequest, AuthResponse, UserResponse, OtpRequestRes


async def request_otp(db: AsyncSession, phone: str) -> OtpRequestRes:
    """Generate and store an OTP for the given phone number."""
    # Generate 6-digit OTP
    code = f"{secrets.randbelow(1000000):06d}"
    code_hash = bcrypt.hashpw(code.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=120)

    # Invalidate existing OTPs for this phone
    await db.execute(delete(OtpCode).where(OtpCode.phone == phone))
    
    otp_record = OtpCode(
        phone=phone,
        code_hash=code_hash,
        expires_at=expires_at,
        attempts=0
    )
    db.add(otp_record)
    await db.commit()

    # Echo in dev if configured (we don't have a DEV_OTP_ECHO setting yet, but we'll use ENV)
    dev_otp = code if getattr(settings, "ENV", "development") != "production" else None

    return OtpRequestRes(
        ok=True,
        expires_in_s=120,
        dev_otp=dev_otp
    )


async def _verify_otp_internal(db: AsyncSession, phone: str, code: str) -> bool:
    result = await db.execute(select(OtpCode).where(OtpCode.phone == phone))
    otp_record = result.scalar_one_or_none()

    if not otp_record:
        return False
        
    # Check expiry or max attempts (5)
    if otp_record.attempts >= 5 or otp_record.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        await db.execute(delete(OtpCode).where(OtpCode.phone == phone))
        await db.commit()
        return False
        
    otp_record.attempts += 1
    await db.commit()
    
    if not bcrypt.checkpw(code.encode('utf-8'), otp_record.code_hash.encode('utf-8')):
        return False
        
    return True


async def verify_otp(db: AsyncSession, phone: str, code: str) -> AuthResponse:
    """Verify OTP and return token+user if exists."""
    is_valid = await _verify_otp_internal(db, phone, code)
    if not is_valid:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired OTP"
        )
        
    # Find user
    result = await db.execute(select(User).where(User.phone == phone))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )
        
    # Generate token
    token = create_access_token({"user_id": user.id, "role": user.role.upper()})

    # Delete OTP upon successful login
    await db.execute(delete(OtpCode).where(OtpCode.phone == phone))
    await db.commit()

    return AuthResponse(
        user=UserResponse.model_validate(user),
        token=token,
    )


async def register_user(db: AsyncSession, payload: RegisterRequest) -> AuthResponse:
    """Register a new user after verifying OTP."""
    # Check phone uniqueness
    result = await db.execute(select(User).where(User.phone == payload.phone))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=409,
            detail="Phone number already registered"
        )
        
    is_valid = await _verify_otp_internal(db, payload.phone, payload.code)
    if not is_valid:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired OTP"
        )

    # Create user
    user = User(
        name=payload.name,
        phone=payload.phone,
        role=payload.role.upper(),
        locale=payload.locale,
        district_id=payload.district_id,
        village=payload.village,
        lat=payload.lat,
        lng=payload.lng,
    )
    db.add(user)
    await db.flush()

    # Create role-specific profile
    if payload.role.upper() == "FARMER" or payload.role.upper() == "FPO_ADMIN":
        farmer = Farmer(user_id=user.id)
        db.add(farmer)
    elif payload.role.upper() == "BUYER":
        buyer = Buyer(user_id=user.id, company_name=payload.company_name)
        db.add(buyer)

    await db.commit()
    await db.refresh(user)

    # Clean up OTP
    await db.execute(delete(OtpCode).where(OtpCode.phone == payload.phone))
    await db.commit()

    token = create_access_token({"user_id": user.id, "role": user.role.upper()})

    return AuthResponse(
        user=UserResponse.model_validate(user),
        token=token,
    )
