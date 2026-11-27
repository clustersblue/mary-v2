from datetime import datetime, timedelta
from typing import Optional
import jwt
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.core.sessions import session_is_expired, session_store
from app.db.session import get_db
from app.models.user import User

http_bearer = HTTPBearer(auto_error=False)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Creates a cryptographically signed JWT access token.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

async def get_current_user(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer),
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Validates bearer token from Authorization header.
    Supports stateful session tokens (mary_tok_...) and standard JWTs.
    Strictly enforces token validation and rejects anonymous/invalid access with 401 Unauthorized.
    """
    token = None
    if auth and auth.credentials:
        token = auth.credentials.strip()
    elif authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1].strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing or malformed.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = None

    # Opaque login tokens are stored in Redis (or this process, if Redis is down).
    if token.startswith("mary_tok_"):
        session_data = await session_store.get(token)
        if not session_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired authentication token.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if session_is_expired(session_data.get("created_at")):
            await session_store.delete(token)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session has expired. Please log in again.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user_id = session_data.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload.",
                headers={"WWW-Authenticate": "Bearer"},
            )
    else:
        # Signed JWT access tokens.
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_id = payload.get("sub") or payload.get("user_id") or payload.get("id")
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token payload.",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        except jwt.PyJWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired authentication token.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # 3. Verify user exists and is active in database
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User associated with this token does not exist.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account has been deactivated. Please contact your system administrator.",
        )

    if user.carer_status_id == 5:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is currently suspended. Please contact your coordinator.",
        )

    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Ensures user is authenticated and active.
    """
    return current_user

def is_admin_user(user: User) -> bool:
    """
    Returns True if user is a System Administrator (role 1 or is_admin flag).
    """
    return bool(user.is_admin) or getattr(user, "role", None) == 1

def is_staff_user(user: User) -> bool:
    """
    Returns True if user is Staff or Administrator (role 1, role 2, or is_admin flag).
    """
    return is_admin_user(user) or getattr(user, "role", None) in (1, 2)

def has_finance_access(user: User) -> bool:
    """
    Returns True if user is authorized to manage Finance, Payroll, and Invoicing.
    Matches Legacy MenuBar parity: Administrator, or Staff (role 1 or 2) with is_admin == 1.
    """
    if is_admin_user(user):
        return True
    return bool(user.is_admin) and getattr(user, "role", None) in (1, 2)

async def get_current_admin_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Role-based access guard: restricts access to System Administrators.
    """
    if not is_admin_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Administrator access required.",
        )
    return current_user

async def get_current_staff_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Role-based access guard: restricts access to Staff and Administrators (roles 1, 2).
    """
    if not is_staff_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Staff or Administrator access required.",
        )
    return current_user

async def get_current_finance_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Role-based access guard: restricts access to Finance & Payroll managers.
    """
    if not has_finance_access(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Financial and Payroll administrative access required.",
        )
    return current_user

