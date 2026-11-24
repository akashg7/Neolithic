from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.config import settings
from app.dependencies.repositories import get_user_repository
from app.models.user import User
from app.repositories.user_repository import IUserRepository

security = HTTPBearer()


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    users: IUserRepository = Depends(get_user_repository),
) -> User:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        user_id: int = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = await users.get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


optional_security = HTTPBearer(auto_error=False)


async def get_optional_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(optional_security)],
    users: IUserRepository = Depends(get_user_repository),
) -> User | None:
    """Like `get_current_user`, but a request with no Authorization header is a
    guest (None). A token that IS sent but is invalid or expired is still a 401 —
    a bad token is never silently downgraded to guest."""
    if credentials is None:
        return None
    return await get_current_user(credentials, users)


def require_role(*roles: str):
    """Dependency factory: require the current user to have one of the given roles."""
    allowed = {r.upper() for r in roles}

    async def _check(user: User = Depends(get_current_user)):
        if (user.role or "").upper() not in allowed:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)  # 404 not 403
        return user
    return _check
