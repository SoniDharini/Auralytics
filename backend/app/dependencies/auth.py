import uuid
from typing import Optional
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidCredentialsException, TokenExpiredException, UserInactiveException
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User

security_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and validate JWT Bearer token, then load current authenticated active user."""
    if not credentials:
        raise InvalidCredentialsException(detail="Authentication credentials required")

    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload:
        raise InvalidCredentialsException(detail="Invalid or expired access token")

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise InvalidCredentialsException(detail="Token payload missing subject")

    try:
        user_uuid = uuid.UUID(user_id_str)
    except ValueError:
        raise InvalidCredentialsException(detail="Invalid user identification format")

    stmt = select(User).where(User.id == user_uuid)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise InvalidCredentialsException(detail="User no longer exists")

    if not user.is_active:
        raise UserInactiveException()

    return user


async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Optional user authentication for public endpoints with personalized context."""
    if not credentials:
        return None
    try:
        return await get_current_user(credentials, db)
    except Exception:
        return None
