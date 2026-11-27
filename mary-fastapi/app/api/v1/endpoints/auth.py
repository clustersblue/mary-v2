import hmac
import logging
import secrets
import smtplib
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, status, Header, Request, BackgroundTasks
import bcrypt
from pydantic import BaseModel, EmailStr
from sqlalchemy import or_, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.core.rate_limit import client_address, enforce_rate_limit
from app.db.session import get_db
import app.models.master_data
from app.models.user import User
from app.core.security import get_current_active_user
from app.core.sessions import SessionUnavailable, session_store

router = APIRouter()
logger = logging.getLogger(__name__)
RESET_MAX_AGE = timedelta(minutes=60)
RESET_RESPONSE = {
    "success": True,
    "message": "If the email is registered, a password reset link has been sent.",
}

class LoginRequest(BaseModel):
    username: str
    password: str
    rememberme: Optional[bool] = False

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    email: EmailStr
    password: str
    password_confirmation: str

class AccountUpdateRequest(BaseModel):
    first_name: Optional[str] = None
    surname: Optional[str] = None
    username: Optional[str] = None
    email: Optional[str] = None
    mobile_number: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_number: Optional[str] = None
    password: Optional[str] = None

def password_is_hashed(stored: Optional[str]) -> bool:
    return bool(stored) and stored.startswith(("$2a$", "$2b$", "$2y$"))

def verify_password(plain_password: str, hashed_password: Optional[str]) -> bool:
    if not hashed_password or not plain_password:
        return False
    if password_is_hashed(hashed_password):
        norm_hash = "$2b$" + hashed_password[4:] if hashed_password.startswith("$2y$") else hashed_password
        try:
            return bcrypt.checkpw(plain_password.encode("utf-8")[:72], norm_hash.encode("utf-8"))
        except Exception:
            return False
    # One successful login upgrades a legacy plaintext value to bcrypt.
    if len(plain_password) != len(hashed_password):
        return False
    return hmac.compare_digest(plain_password, hashed_password)

def hash_password(password: str) -> str:
    pwd_bytes = password.encode("utf-8")[:72]
    return bcrypt.hashpw(pwd_bytes, bcrypt.gensalt(12)).decode("utf-8")

def assess_reset_token(stored: Optional[str], supplied: Optional[str], created_at: Optional[datetime], now: Optional[datetime] = None) -> str:
    """Return ok, invalid, or expired. A missing or magic token is invalid."""
    if not stored or not supplied:
        return "invalid"
    stored_text = str(stored)
    supplied_text = str(supplied)
    if len(stored_text) != len(supplied_text) or not hmac.compare_digest(stored_text, supplied_text):
        return "invalid"
    if created_at is None:
        return "invalid"
    if created_at.tzinfo is not None:
        created_at = created_at.astimezone(timezone.utc).replace(tzinfo=None)
    current = now or datetime.utcnow()
    if current - created_at > RESET_MAX_AGE:
        return "expired"
    return "ok"

def _reset_link(token: str, email: str) -> Optional[str]:
    base = (settings.PUBLIC_BASE_URL or "").rstrip("/")
    if not base:
        return None
    return f"{base}/reset-password?token={quote(token, safe='')}&email={quote(email, safe='')}"

def send_smtp_email(to_email: str, subject: str, reset_url: str) -> bool:
    """Send the reset message. The link is not written to the care-file volume."""
    if not settings.SMTP_HOST or not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        logger.error("SMTP is not configured. Password reset email was not sent.")
        return False

    sender = settings.SMTP_FROM or settings.SMTP_USER
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px;">
        <h2 style="color: #2c3e50;">SMTC - Reset Password Notification</h2>
        <p>You are receiving this email because we received a password reset request for your account.</p>
        <div style="text-align: center; margin: 30px 0;">
            <a href="{reset_url}" style="background-color: #3b82f6; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; font-weight: bold;">Reset Password</a>
        </div>
        <p style="color: #64748b; font-size: 14px;">This password reset link will expire in 60 minutes.</p>
        <p style="color: #64748b; font-size: 14px;">If you did not request a password reset, no further action is required.</p>
        <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 20px 0;" />
        <p style="color: #94a3b8; font-size: 12px;">If you're having trouble clicking the "Reset Password" button, copy and paste the URL below into your web browser:<br/><a href="{reset_url}">{reset_url}</a></p>
    </div>
    """

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = to_email
        msg.attach(MIMEText(html_content, "html"))
        with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20) as server:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(sender, [to_email], msg.as_string())
        logger.info("Password reset email handed to SMTP")
        return True
    except Exception:
        logger.exception("Password reset email was not sent")
        return False

# ==============================================================================
# --- AUTHENTICATION ENDPOINTS ---
# ==============================================================================

def serialize_user(user: User) -> dict:
    role_val = int(user.role) if user.role is not None else (1 if user.is_admin else 3)
    return {
        "id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "surname": user.surname,
        "full_name": f"{user.first_name} {user.surname}".strip(),
        "email": user.email,
        "mobile_number": user.mobile,
        "emergency_contact_name": user.emergency_contact_name,
        "emergency_contact_number": user.emergency_contact_number,
        "user_id": user.user_id,
        "is_admin": 1 if user.is_admin else 0,
        "role": role_val
    }

@router.post("/login")
async def login(req: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    address = client_address(request)
    enforce_rate_limit(f"login-ip:{address}", limit=20, window_seconds=300)
    enforce_rate_limit(f"login-user:{req.username.strip().lower()[:200]}", limit=10, window_seconds=300)
    result = await db.execute(
        select(User).where(
            or_(User.username == req.username, User.email == req.username)
        )
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password. Please try again."
        )

    if user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account has been deactivated. Please contact your system administrator."
        )

    if user.carer_status_id == 5:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is currently suspended. Please contact your coordinator."
        )

    if not verify_password(req.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password. Please try again."
        )

    if not password_is_hashed(user.password):
        user.password = hash_password(req.password)
        user.updated_at = datetime.utcnow()
        await db.commit()

    # Issue session / bearer token
    token = f"mary_tok_{secrets.token_hex(24)}"

    user_data = serialize_user(user)

    try:
        await session_store.put(token, {
            "user": user_data,
            "user_id": user.id,
            "created_at": datetime.utcnow()
        })
    except SessionUnavailable:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Sign-in is temporarily unavailable. Try again shortly.",
        )

    return {
        "success": True,
        "token": token,
        "user": user_data,
        "message": "Login successful"
    }

@router.post("/logout")
async def logout(authorization: Optional[str] = Header(None)):
    if authorization and authorization.startswith("Bearer "):
        tok = authorization.split(" ")[1]
        await session_store.delete(tok)
    return {
        "success": True,
        "message": "Successfully logged out"
    }

@router.get("/me")
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user)
):
    """
    Validates token and preflight session state.
    Returns 401 Unauthorized if token is missing, invalid, or expired.
    """
    return serialize_user(current_user)

# ==============================================================================
# --- PASSWORD RESET & FORGOT WORKFLOW ---
# ==============================================================================

@router.post("/forgot-password")
async def forgot_password(
    req: ForgotPasswordRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    enforce_rate_limit(f"forgot-ip:{client_address(request)}", limit=5, window_seconds=900)
    enforce_rate_limit(f"forgot-email:{str(req.email).lower()}", limit=5, window_seconds=900)
    result = await db.execute(select(User).where(User.email == req.email, User.deleted_at.is_(None)))
    user = result.scalar_one_or_none()

    if user:
        reset_token = secrets.token_urlsafe(32)
        reset_link = _reset_link(reset_token, user.email)
        if reset_link is None:
            logger.error("PUBLIC_BASE_URL is empty. Password reset email was not sent.")
        else:
            await db.execute(text("DELETE FROM password_reset_tokens WHERE email = :email"), {"email": user.email})
            await db.execute(
                text("INSERT INTO password_reset_tokens (email, token, created_at) VALUES (:email, :token, NOW())"),
                {"email": user.email, "token": reset_token}
            )
            await db.commit()
            background_tasks.add_task(
                send_smtp_email,
                user.email,
                "SMTC - Reset Password Notification",
                reset_link
            )

    return RESET_RESPONSE

@router.post("/reset-password")
async def reset_password(req: ResetPasswordRequest, request: Request, db: AsyncSession = Depends(get_db)):
    enforce_rate_limit(f"reset-ip:{client_address(request)}", limit=10, window_seconds=900)
    if len(req.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters in length."
        )

    if req.password != req.password_confirmation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password and confirmation do not match."
        )

    token_query = await db.execute(
        text("SELECT token, created_at FROM password_reset_tokens WHERE email = :email ORDER BY created_at DESC LIMIT 1"),
        {"email": req.email}
    )
    token_row = token_query.fetchone()
    stored_token = token_row[0] if token_row else None
    token_created = token_row[1] if token_row else None
    verdict = assess_reset_token(stored_token, req.token, token_created)
    if verdict == "expired":
        await db.execute(text("DELETE FROM password_reset_tokens WHERE email = :email"), {"email": req.email})
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset token has expired. Please request a new link."
        )
    if verdict != "ok":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid password reset token."
        )

    result = await db.execute(select(User).where(User.email == req.email, User.deleted_at.is_(None)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid password reset token."
        )

    # Update password with bcrypt hash
    user.password = hash_password(req.password)
    user.updated_at = datetime.utcnow()

    # Clean up token in DB
    await db.execute(text("DELETE FROM password_reset_tokens WHERE email = :email"), {"email": req.email})
    await db.commit()

    return {
        "success": True,
        "message": "Password reset successfully"
    }

# ==============================================================================
# --- "MY ACCOUNT" MANAGEMENT ENDPOINT ---
# ==============================================================================

@router.post("/updateaccount/{user_id}")
async def update_account(
    user_id: int,
    req: AccountUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Updates the authenticated user's account profile and credentials.
    Replicates legacy /api/updateaccount/{id} endpoint with full parity.
    Strictly verifies that user is editing their own profile or has administrator privileges.
    """
    if current_user.id != user_id and not (bool(current_user.is_admin) or getattr(current_user, "role", None) == 1):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to modify another user's account."
        )

    result = await db.execute(select(User).where(User.id == user_id, User.deleted_at.is_(None)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User account not found.")

    if req.first_name is not None:
        user.first_name = req.first_name.strip()
    if req.surname is not None:
        user.surname = req.surname.strip()
    if req.username is not None:
        user.username = req.username.strip()
    if req.email is not None:
        user.email = req.email.strip()
    if req.mobile_number is not None:
        user.mobile = req.mobile_number.strip()
    if req.emergency_contact_name is not None:
        user.emergency_contact_name = req.emergency_contact_name.strip()
    if req.emergency_contact_number is not None:
        user.emergency_contact_number = req.emergency_contact_number.strip()

    if req.password and req.password.strip():
        if len(req.password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be at least 8 characters."
            )
        user.password = hash_password(req.password.strip())

    user.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(user)

    updated_data = serialize_user(user)

    if authorization and authorization.startswith("Bearer "):
        tok = authorization.split(" ")[1]
        await session_store.update_user(tok, updated_data)

    return {
        "success": True,
        "message": "Account updated successfully",
        "data": updated_data
    }
