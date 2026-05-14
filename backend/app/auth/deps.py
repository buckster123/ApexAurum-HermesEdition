"""
Authentication Dependencies
"""

from typing import Optional
from uuid import uuid4, UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.user import User
from app.auth.jwt import verify_token

settings = get_settings()

# Bearer token security scheme
security = HTTPBearer()


async def _get_or_create_default_user(db: AsyncSession) -> User:
    """Get or create the default local user."""
    result = await db.execute(
        select(User).where(User.email == settings.local_default_user_email)
    )
    user = result.scalar_one_or_none()
    if user:
        return user

    from app.auth.password import hash_password
    user = User(
        id=uuid4(),
        email=settings.local_default_user_email,
        password_hash=hash_password(settings.local_default_user_password),
        display_name="Local User",
        is_admin=True,
    )
    db.add(user)
    await db.flush()
    return user


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Dependency to get the current authenticated user.

    In LOCAL_MODE, bypasses auth and returns the default user.
    """
    if settings.local_mode:
        return await _get_or_create_default_user(db)

    token = credentials.credentials

    # Verify token
    payload = verify_token(token, token_type="access")
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Parse user ID from payload (with error handling for malformed tokens)
    try:
        user_id = UUID(payload["sub"])
    except (KeyError, ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user from database
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Optional authentication - returns None if not authenticated.

    Useful for endpoints that work both with and without auth.
    """
    if settings.local_mode:
        return await _get_or_create_default_user(db)

    if credentials is None:
        return None

    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None
