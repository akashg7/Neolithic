"""Authentication service: OTP issue/verify, registration, profile lookup.

Owner: Member 1. Depends only on repository *interfaces* (DIP). Concrete
SQLAlchemy repositories are injected by `get_auth_service`, and tests inject
in-memory ones. Profiles are created through `UserFactory` (Factory Method),
never by instantiating `Farmer` / `Buyer` here.

Single responsibility split:
  * `OtpService`  — generate, hash, throttle, expire and check OTP codes.
  * `AuthService` — orchestrate login/registration and mint JWTs.
"""
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, status

from app.config import settings
from app.dependencies.auth import create_access_token
from app.dependencies.repositories import (
    get_fpo_repository,
    get_otp_repository,
    get_user_repository,
)
from app.domain.factories.user_factory import UserFactory
from app.models.otp import OtpCode
from app.models.user import User
from app.repositories.fpo_repository import IFpoRepository
from app.repositories.otp_repository import IOtpRepository
from app.repositories.user_repository import IUserRepository
from app.schemas.auth import AuthResponse, OtpRequestRes, RegisterRequest, UserResponse


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(dt: datetime) -> datetime:
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


class OtpService:
    """OTP lifecycle: 6-digit code, bcrypt-hashed at rest, TTL, attempt cap, throttle."""

    def __init__(
        self,
        otp_repo: IOtpRepository,
        ttl_seconds: int = settings.OTP_TTL_SECONDS,
        max_attempts: int = settings.OTP_MAX_ATTEMPTS,
        max_requests: int = settings.OTP_MAX_REQUESTS_PER_WINDOW,
        window_seconds: int = settings.OTP_THROTTLE_WINDOW_SECONDS,
    ):
        self.otp_repo = otp_repo
        self.ttl_seconds = ttl_seconds
        self.max_attempts = max_attempts
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    async def issue(self, phone: str) -> str:
        """Create a new OTP for `phone` and return the plaintext code.

        Raises 429 if `max_requests` codes were already issued in the window.
        Older codes stay in the table until the window passes so the throttle
        can count them. Only the newest code can be verified.
        """
        now = _utcnow()
        window_start = now - timedelta(seconds=self.window_seconds)
        await self.otp_repo.delete_issued_before(phone, window_start)
        if await self.otp_repo.count_issued_since(phone, window_start) >= self.max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many OTP requests. Please try again later.",
            )

        code = f"{secrets.randbelow(1_000_000):06d}"
        code_hash = bcrypt.hashpw(code.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        await self.otp_repo.create(OtpCode(
            phone=phone,
            code_hash=code_hash,
            attempts=0,
            expires_at=now + timedelta(seconds=self.ttl_seconds),
            created_at=now,
        ))
        await self.otp_repo.commit()
        return code

    async def check(self, phone: str, code: str) -> bool:
        """True if `code` matches the newest live OTP. Every try is counted, and
        the count is committed before returning so a 401 can't roll it back."""
        record = await self.otp_repo.latest_for_phone(phone)
        if record is None:
            return False
        if record.attempts >= self.max_attempts or _as_utc(record.expires_at) < _utcnow():
            return False

        record.attempts += 1
        await self.otp_repo.commit()
        return bcrypt.checkpw(code.encode("utf-8"), record.code_hash.encode("utf-8"))

    async def consume(self, phone: str) -> None:
        """Invalidate every OTP for `phone` after a successful login/registration."""
        await self.otp_repo.delete_for_phone(phone)


class AuthService:

    def __init__(
        self,
        user_repo: IUserRepository,
        otp_service: OtpService,
        fpo_repo: Optional[IFpoRepository] = None,
        factory: type[UserFactory] = UserFactory,
    ):
        self.user_repo = user_repo
        self.otp_service = otp_service
        self.fpo_repo = fpo_repo
        self.factory = factory

    @staticmethod
    def _issue_token(user: User) -> AuthResponse:
        token = create_access_token({"user_id": user.id, "role": user.role.upper()})
        return AuthResponse(user=UserResponse.model_validate(user), token=token)

    async def request_otp(self, phone: str) -> OtpRequestRes:
        code = await self.otp_service.issue(phone)
        dev_otp = code if settings.ENV != "production" else None
        return OtpRequestRes(ok=True, expires_in_s=self.otp_service.ttl_seconds, dev_otp=dev_otp)

    async def verify_otp(self, phone: str, code: str) -> AuthResponse:
        """Login an existing user with an OTP."""
        if not await self.otp_service.check(phone, code):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired OTP")

        user = await self.user_repo.get_by_phone(phone)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        await self.otp_service.consume(phone)
        await self.user_repo.commit()
        return self._issue_token(user)

    async def register(self, payload: RegisterRequest) -> AuthResponse:
        """Create a User plus its role profile (via UserFactory) atomically."""
        if await self.user_repo.get_by_phone(payload.phone) is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Phone number already registered")

        if not await self.otp_service.check(payload.phone, payload.code):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired OTP")

        role = payload.role  # already normalised to upper-case by the schema
        await self._validate_fpo_link(role, payload.fpo_id)

        district_id = payload.district_id
        user = await self.user_repo.create(User(
            name=payload.name,
            phone=payload.phone,
            role=role,
            locale=payload.locale,
            district_id=int(district_id) if district_id is not None and str(district_id).isdigit() else None,
            village=payload.village,
            lat=payload.lat,
            lng=payload.lng,
        ))

        try:
            profile = self.factory.create_user_profile(user, payload.model_dump())
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
        await self.user_repo.add_profile(profile)

        await self.otp_service.consume(payload.phone)
        await self.user_repo.commit()
        return self._issue_token(user)

    async def _validate_fpo_link(self, role: str, fpo_id: Optional[int]) -> None:
        if fpo_id is None:
            return
        if role != "FARMER":
            # An FPO admin can see member farmers' contact details, so admin
            # linkage is assigned by an operator (seed/admin), not self-claimed.
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only farmers can join an FPO at registration")
        if self.fpo_repo is None or await self.fpo_repo.get_by_id(fpo_id) is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown FPO")

    async def get_profile(self, user_id: int) -> User:
        user = await self.user_repo.get_with_profiles(user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user

    async def update_locale(self, user: User, locale: str) -> None:
        user.locale = locale
        await self.user_repo.update(user)
        await self.user_repo.commit()


def get_auth_service(
    user_repo: IUserRepository = Depends(get_user_repository),
    otp_repo: IOtpRepository = Depends(get_otp_repository),
    fpo_repo: IFpoRepository = Depends(get_fpo_repository),
) -> AuthService:
    return AuthService(user_repo=user_repo, otp_service=OtpService(otp_repo), fpo_repo=fpo_repo)
