"""Auth router — Google ID-token verification, JWT issuance, and session info."""

import logging
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models import User
from app.utils.auth_utils import create_access_token, get_current_user

logger = logging.getLogger("tradinghelper.auth")
router = APIRouter(prefix="/api/auth", tags=["Auth"])


# ── Request / Response schemas ─────────────────────────────────────────────────


class GoogleLoginRequest(BaseModel):
    credential: str  # The Google ID token from the GSI SDK


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    avatar_url: Optional[str]


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post("/google", response_model=TokenResponse)
async def login_with_google(
    body: GoogleLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Accept a Google ID token from the frontend, verify it server-side,
    upsert the User row, and return a signed JWT.
    """
    settings = get_settings()

    if not settings.google_client_id or settings.google_client_id.startswith("REPLACE"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured on this server. Set GOOGLE_CLIENT_ID in .env",
        )

    # Verify the Google ID token
    try:
        google_request = google_requests.Request()
        id_info = google_id_token.verify_oauth2_token(
            body.credential,
            google_request,
            settings.google_client_id,
        )
    except ValueError as exc:
        logger.warning("Google ID token verification failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google credential",
        ) from exc

    google_sub: str = id_info["sub"]
    email: str = id_info.get("email", "")
    name: str = id_info.get("name", email.split("@")[0])
    avatar_url: str | None = id_info.get("picture")

    # Upsert the user
    result = await db.execute(select(User).where(User.google_sub == google_sub))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            google_sub=google_sub,
            email=email,
            name=name,
            avatar_url=avatar_url,
        )
        db.add(user)
        logger.info("New user registered: %s (%s)", name, email)
    else:
        # Update profile fields in case they changed in Google
        user.name = name
        user.avatar_url = avatar_url
        logger.info("Existing user logged in: %s (%s)", name, email)

    await db.commit()
    await db.refresh(user)

    access_token = create_access_token(user)

    return TokenResponse(
        access_token=access_token,
        user={
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "avatar_url": user.avatar_url,
        },
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user's profile (validates the JWT)."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        avatar_url=current_user.avatar_url,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout():
    """
    Stateless logout — the client should discard its JWT.
    This endpoint exists so the frontend has a clean API call to call on sign-out.
    """
    return None
