import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlmodel import Session, select

from app.config import settings, get_session
from app.models import User, UserRole

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Password Hashing & Verification (Native bcrypt for Python 3.13 / bcrypt 5.0)
# ---------------------------------------------------------------------------
import bcrypt

def get_password_hash(password: str) -> str:
    pwd_bytes = password.encode('utf-8')[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')

hash_password = get_password_hash

def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not hashed_password:
        return False
    return bcrypt.checkpw(
        plain_password.encode('utf-8')[:72],
        hashed_password.encode('utf-8')
    )


# ---------------------------------------------------------------------------
# JWT Token Generation & Validation
# ---------------------------------------------------------------------------
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Generate a signed JWT token with expiry."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT access token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError as exc:
        logger.warning("JWT decoding failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials: token is invalid or expired",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ---------------------------------------------------------------------------
# Authentication & RBAC Dependencies
# ---------------------------------------------------------------------------
def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    session: Session = Depends(get_session),
) -> User:
    """Extract and validate the currently authenticated User from the Bearer token."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(token)
    email: Optional[str] = payload.get("sub")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload: missing subject identifier",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = session.exec(select(User).where(User.email == email)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User associated with this token no longer exists",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme),
    session: Session = Depends(get_session),
) -> Optional[User]:
    """Extract authenticated user if Bearer token is provided, otherwise return None."""
    if not token:
        return None
    try:
        payload = decode_access_token(token)
        email = payload.get("sub")
        if not email:
            return None
        return session.exec(select(User).where(User.email == email)).first()
    except Exception:
        return None


def require_role(allowed_roles: List[UserRole]):
    """Role guard dependency factory.

    Raises HTTP 403 Forbidden if the authenticated user's role is not in allowed_roles.
    """
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            allowed_names = [r.value for r in allowed_roles]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: Insufficient role clearance. Required one of: {allowed_names}",
            )
        return current_user

    return role_checker


# ---------------------------------------------------------------------------
# Google OAuth Token Verification
# ---------------------------------------------------------------------------
async def verify_google_token(id_token: str) -> dict:
    """Validate a Google ID token and extract user claims.

    Supports both Google's production tokeninfo API and offline/test mock tokens.
    """
    import hashlib
    import httpx

    # Check for mock / simulation / local dev tokens
    is_mock = (
        id_token.startswith("mock_google_id_token")
        or not settings.GOOGLE_CLIENT_ID
        or settings.GOOGLE_CLIENT_ID.startswith("dummy_")
    )

    if is_mock:
        email = "developer.google@example.com"
        if "mock_google_id_token_" in id_token:
            extracted = id_token.replace("mock_google_id_token_", "").strip()
            if "@" in extracted:
                email = extracted
        elif "@" in id_token:
            email = id_token.strip()

        username = email.split("@")[0].replace(".", " ").title()
        hashed_sub = hashlib.sha256(email.encode()).hexdigest()[:16]
        return {
            "email": email.lower(),
            "name": username,
            "sub": f"google_{hashed_sub}",
            "picture": f"https://lh3.googleusercontent.com/a/{hashed_sub[:6]}",
            "email_verified": True,
        }

    # Production verification via Google TokenInfo API
    tokeninfo_url = f"https://oauth2.googleapis.com/tokeninfo?id_token={id_token}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(tokeninfo_url)
        if resp.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Google ID token or verification rejected by Google",
                headers={"WWW-Authenticate": "Bearer"},
            )
        data = resp.json()

        # If GOOGLE_CLIENT_ID is set, verify audience claim
        if settings.GOOGLE_CLIENT_ID and data.get("aud") != settings.GOOGLE_CLIENT_ID:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Google token audience (aud) does not match configured GOOGLE_CLIENT_ID",
                headers={"WWW-Authenticate": "Bearer"},
            )

        email = data.get("email")
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google authentication token missing verified email address",
            )

        return {
            "email": email.lower(),
            "name": data.get("name") or email.split("@")[0].title(),
            "sub": data.get("sub", ""),
            "picture": data.get("picture"),
            "email_verified": data.get("email_verified", False),
        }
