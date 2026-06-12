import smtplib
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import get_db
from app.models.user import User
from app.schemas.user import LoginRequest, PasswordResetConfirm, PasswordResetRequest, RegisterRequest

router = APIRouter(prefix="/auth", tags=["auth"])

GOOGLE_TOKEN_INFO_URL = "https://oauth2.googleapis.com/tokeninfo"
RESET_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class GoogleTokenRequest(BaseModel):
    id_token: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


def _create_jwt(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": str(user_id), "exp": expire}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def _create_reset_token(email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": email, "exp": expire, "type": "reset"},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def _send_reset_email(to_email: str, token: str):
    reset_url = f"https://yourfrontend.com/reset-password?token={token}"
    msg = MIMEText(f"Click this link to reset your password (valid 30 minutes):\n\n{reset_url}")
    msg["Subject"] = "Hospital Home-Care — Password Reset"
    msg["From"] = "noreply@yourdomain.com"
    msg["To"] = to_email

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(msg)


# ── Email / Password ──────────────────────────────────────────────────────────

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        name=body.name,
        email=body.email,
        password_hash=pwd_context.hash(body.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return {"access_token": _create_jwt(user.user_id), "token_type": "bearer"}


@router.post("/login")
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not user.password_hash or not pwd_context.verify(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return {"access_token": _create_jwt(user.user_id), "token_type": "bearer"}


@router.post("/forgot-password", status_code=status.HTTP_204_NO_CONTENT)
async def forgot_password(body: PasswordResetRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    # Always return 204 even if email not found — prevents email enumeration
    if user and user.password_hash:
        token = _create_reset_token(user.email)
        _send_reset_email(user.email, token)


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(body: PasswordResetConfirm, db: AsyncSession = Depends(get_db)):
    try:
        payload = jwt.decode(body.token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "reset":
            raise ValueError
        email = payload["sub"]
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    user.password_hash = pwd_context.hash(body.new_password)
    await db.commit()


# ── Google OAuth ──────────────────────────────────────────────────────────────

@router.post("/google", response_model=TokenResponse)
async def google_auth(body: GoogleTokenRequest, db: AsyncSession = Depends(get_db)):
    async with httpx.AsyncClient() as client:
        resp = await client.get(GOOGLE_TOKEN_INFO_URL, params={"id_token": body.id_token})

    if resp.status_code != 200:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google token")

    info = resp.json()
    if info.get("aud") != settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token audience mismatch")

    email: str = info["email"]
    name: str = info.get("name", email.split("@")[0])
    oauth_id: str = info["sub"]

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(name=name, email=email, oauth_provider="google", oauth_id=oauth_id)
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return TokenResponse(access_token=_create_jwt(user.user_id))
