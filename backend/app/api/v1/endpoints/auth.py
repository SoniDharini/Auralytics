import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Cookie, Depends, Response, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    DuplicateEmailException,
    InvalidCredentialsException,
    TokenExpiredException,
    UserInactiveException,
)
from app.core.security import (
    create_access_token,
    get_password_hash,
    hash_token,
    verify_password,
)
from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.refresh_session import RefreshSession
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    MessageResponse,
    RefreshResponse,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _set_refresh_cookie(response: Response, raw_refresh_token: str) -> None:
    """Helper to set a secure, HttpOnly refresh cookie."""
    max_age = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    response.set_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        value=raw_refresh_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=max_age,
        path="/",
    )


def _clear_refresh_cookie(response: Response) -> None:
    """Helper to remove the refresh cookie upon logout."""
    response.delete_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        path="/",
    )


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
async def register(
    data: RegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    # Check for duplicate email
    stmt = select(User).where(User.email == data.email)
    result = await db.execute(stmt)
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise DuplicateEmailException()

    # Create new user with Argon2 hashed password
    hashed_pwd = get_password_hash(data.password)
    user = User(
        full_name=data.full_name,
        email=data.email,
        password_hash=hashed_pwd,
        company_name=data.company_name,
        role=data.role,
        is_active=True,
        last_login_at=datetime.now(timezone.utc),
    )
    db.add(user)
    await db.flush()  # populate user.id

    # Create secure refresh session
    raw_refresh_token = secrets.token_urlsafe(48)
    token_h = hash_token(raw_refresh_token)
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    session_record = RefreshSession(
        user_id=user.id,
        token_hash=token_h,
        expires_at=expires_at,
    )
    db.add(session_record)
    await db.commit()
    await db.refresh(user)

    # Issue JWT access token and set refresh cookie
    access_token = create_access_token(subject=user.id, role=user.role)
    _set_refresh_cookie(response, raw_refresh_token)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Sign in with email and password",
)
async def login(
    data: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    # Find user by email
    stmt = select(User).where(User.email == data.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not verify_password(data.password, user.password_hash):
        raise InvalidCredentialsException()

    if not user.is_active:
        raise UserInactiveException()

    # Update last login timestamp
    user.last_login_at = datetime.now(timezone.utc)

    # Create new refresh session
    raw_refresh_token = secrets.token_urlsafe(48)
    token_h = hash_token(raw_refresh_token)
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    session_record = RefreshSession(
        user_id=user.id,
        token_hash=token_h,
        expires_at=expires_at,
    )
    db.add(session_record)
    await db.commit()
    await db.refresh(user)

    # Issue tokens
    access_token = create_access_token(subject=user.id, role=user.role)
    _set_refresh_cookie(response, raw_refresh_token)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/refresh",
    response_model=RefreshResponse,
    summary="Rotate refresh token and issue new access token",
)
async def refresh_session(
    response: Response,
    refresh_token: Optional[str] = Cookie(default=None, alias=settings.REFRESH_COOKIE_NAME),
    db: AsyncSession = Depends(get_db),
):
    if not refresh_token:
        raise InvalidCredentialsException(detail="No refresh session provided")

    token_h = hash_token(refresh_token)
    now = datetime.now(timezone.utc)

    # Look up active refresh session
    stmt = select(RefreshSession).where(
        RefreshSession.token_hash == token_h,
        RefreshSession.revoked_at.is_(None),
    )
    result = await db.execute(stmt)
    session_record = result.scalar_one_or_none()

    if not session_record:
        _clear_refresh_cookie(response)
        raise TokenExpiredException(detail="Session expired or revoked")

    expires_at = (
        session_record.expires_at.replace(tzinfo=timezone.utc)
        if session_record.expires_at.tzinfo is None
        else session_record.expires_at
    )
    if expires_at <= now:
        _clear_refresh_cookie(response)
        raise TokenExpiredException(detail="Session expired or revoked")

    # Load associated user
    user_stmt = select(User).where(User.id == session_record.user_id)
    user_res = await db.execute(user_stmt)
    user = user_res.scalar_one_or_none()

    if not user or not user.is_active:
        _clear_refresh_cookie(response)
        raise InvalidCredentialsException(detail="User inactive or removed")

    # Rotate refresh session
    session_record.revoked_at = now

    new_raw_refresh_token = secrets.token_urlsafe(48)
    new_token_h = hash_token(new_raw_refresh_token)
    new_expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    new_session = RefreshSession(
        user_id=user.id,
        token_hash=new_token_h,
        expires_at=new_expires_at,
    )
    db.add(new_session)
    await db.commit()

    # Issue new access token & update cookie
    new_access_token = create_access_token(subject=user.id, role=user.role)
    _set_refresh_cookie(response, new_raw_refresh_token)

    return RefreshResponse(
        access_token=new_access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Revoke refresh session and sign out",
)
async def logout(
    response: Response,
    refresh_token: Optional[str] = Cookie(default=None, alias=settings.REFRESH_COOKIE_NAME),
    db: AsyncSession = Depends(get_db),
):
    if refresh_token:
        token_h = hash_token(refresh_token)
        now = datetime.now(timezone.utc)
        stmt = (
            update(RefreshSession)
            .where(RefreshSession.token_hash == token_h, RefreshSession.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        await db.execute(stmt)
        await db.commit()

    _clear_refresh_cookie(response)
    return MessageResponse(message="Successfully signed out")


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current authenticated user profile",
)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    return UserResponse.model_validate(current_user)
