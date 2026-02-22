"""
Authentication Endpoints
"""

import secrets
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.auth import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token,
    get_current_user,
)

router = APIRouter()


# Schemas
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    display_name: str | None = None
    terms_accepted: bool = False


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


# Endpoints
@router.post("/register", response_model=TokenResponse)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """Register a new user."""
    # Check if email already exists
    result = await db.execute(
        select(User).where(User.email == request.email)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Require terms acceptance
    if not request.terms_accepted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must accept the Terms of Service to create an account"
        )

    # Create user
    from datetime import datetime, timezone
    user = User(
        email=request.email,
        password_hash=hash_password(request.password),
        display_name=request.display_name,
        terms_accepted_at=datetime.now(timezone.utc),
    )
    db.add(user)
    await db.flush()  # Get the user ID

    # Generate tokens
    access_token = create_access_token(user.id, user.email)
    refresh_token = create_refresh_token(user.id, user.email)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """Login with email and password."""
    # Find user
    result = await db.execute(
        select(User).where(User.email == request.email)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Generate tokens
    access_token = create_access_token(user.id, user.email)
    refresh_token = create_refresh_token(user.id, user.email)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(
    request: RefreshRequest,
    db: AsyncSession = Depends(get_db)
):
    """Refresh access token using refresh token."""
    # Verify refresh token
    payload = verify_token(request.refresh_token, token_type="refresh")
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )

    # Get user
    from uuid import UUID
    user_id = UUID(payload["sub"])
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    # Generate new tokens
    access_token = create_access_token(user.id, user.email)
    refresh_token = create_refresh_token(user.id, user.email)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    """Get current authenticated user info (used by admin panel)."""
    return {
        "id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "is_admin": getattr(user, "is_admin", False),
    }


@router.post("/logout")
async def logout():
    """
    Logout (client-side token invalidation).

    Note: For proper server-side invalidation, implement token blacklisting in Redis.
    """
    return {"message": "Logged out successfully"}


# ---- Device Code Pairing (TV-style auth for Quest VR) ----

DEVICE_CODE_CHARS = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
DEVICE_CODE_LENGTH = 4
DEVICE_CODE_TTL = 300  # 5 minutes

# In-memory store: {code: {created_at, status, tokens}}
_device_codes: dict[str, dict] = {}


def _cleanup_expired_codes() -> None:
    now = time.time()
    expired = [c for c, d in _device_codes.items() if now - d["created_at"] > DEVICE_CODE_TTL]
    for c in expired:
        del _device_codes[c]


def _generate_device_code() -> str:
    _cleanup_expired_codes()
    for _ in range(100):
        code = "".join(secrets.choice(DEVICE_CODE_CHARS) for _ in range(DEVICE_CODE_LENGTH))
        if code not in _device_codes:
            return code
    raise HTTPException(status_code=503, detail="Unable to generate unique code")


class DeviceCodeResponse(BaseModel):
    device_code: str
    poll_interval: int = 3
    expires_in: int = 300


class DevicePollRequest(BaseModel):
    device_code: str


class DevicePollResponse(BaseModel):
    status: str
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: Optional[str] = None


class DeviceConfirmRequest(BaseModel):
    device_code: str


@router.post("/device-code", response_model=DeviceCodeResponse)
async def request_device_code():
    """Generate a device pairing code for VR/TV-style authentication."""
    code = _generate_device_code()
    _device_codes[code] = {
        "created_at": time.time(),
        "status": "pending",
        "tokens": None,
    }
    return DeviceCodeResponse(
        device_code=code,
        poll_interval=3,
        expires_in=DEVICE_CODE_TTL,
    )


@router.post("/device-poll", response_model=DevicePollResponse)
async def poll_device_code(request: DevicePollRequest):
    """Poll for device code confirmation status."""
    code = request.device_code.upper().strip()
    entry = _device_codes.get(code)
    if not entry:
        return DevicePollResponse(status="expired")
    if time.time() - entry["created_at"] > DEVICE_CODE_TTL:
        del _device_codes[code]
        return DevicePollResponse(status="expired")
    if entry["status"] == "confirmed" and entry["tokens"]:
        tokens = entry["tokens"]
        del _device_codes[code]
        return DevicePollResponse(
            status="confirmed",
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            token_type="bearer",
        )
    return DevicePollResponse(status="pending")


@router.post("/device-confirm")
async def confirm_device_code(
    request: DeviceConfirmRequest,
    user: User = Depends(get_current_user),
):
    """Confirm a device pairing code (authenticated user binds their account)."""
    code = request.device_code.upper().strip()
    entry = _device_codes.get(code)
    if not entry:
        raise HTTPException(status_code=404, detail="Code not found or expired")
    if time.time() - entry["created_at"] > DEVICE_CODE_TTL:
        del _device_codes[code]
        raise HTTPException(status_code=410, detail="Code expired")
    if entry["status"] == "confirmed":
        raise HTTPException(status_code=409, detail="Code already used")

    access_token = create_access_token(user.id, user.email)
    refresh_token = create_refresh_token(user.id, user.email)
    entry["status"] = "confirmed"
    entry["tokens"] = {
        "access_token": access_token,
        "refresh_token": refresh_token,
    }
    return {"message": "Device paired successfully", "user_email": user.email}
