import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, EmailStr
from sqlmodel import Session, select

from app.config import settings, get_session
from app.models import User, UserRole
from app.auth import (
    get_password_hash,
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    verify_google_token,
    require_role,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication & RBAC"])


# ---------------------------------------------------------------------------
# Request & Response Schemas
# ---------------------------------------------------------------------------
class UserRegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str


class UserLoginRequest(BaseModel):
    email: str
    password: str


class GoogleAuthRequest(BaseModel):
    id_token: Optional[str] = None
    code: Optional[str] = None
    redirect_uri: Optional[str] = None
    requested_role: Optional[UserRole] = None


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: UserRole
    auth_provider: Optional[str] = "local"
    picture_url: Optional[str] = None
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: UserRole
    email: str
    full_name: str
    picture_url: Optional[str] = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
def register(
    req: UserRegisterRequest,
    session: Session = Depends(get_session),
) -> UserResponse:
    """Register a new user.

    The first registered user is automatically assigned ADMIN role.
    All subsequent registrations default to DEVELOPER role.
    """
    clean_email = req.email.strip().lower()
    if not clean_email or not req.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email and password cannot be empty",
        )

    # Check for duplicate email
    existing_user = session.exec(select(User).where(User.email == clean_email)).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists",
        )

    # First user becomes ADMIN; others become DEVELOPER
    existing_count = len(session.exec(select(User)).all())
    assigned_role = UserRole.ADMIN if existing_count == 0 else UserRole.DEVELOPER

    try:
        hashed_pwd = get_password_hash(req.password)
        new_user = User(
            email=clean_email,
            hashed_password=hashed_pwd,
            full_name=req.full_name.strip(),
            role=assigned_role,
            auth_provider="local",
        )
        session.add(new_user)
        session.commit()
        session.refresh(new_user)
    except Exception as exc:
        session.rollback()
        logger.exception("Failed to create user account for %s: %s", clean_email, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal database error while creating user account: {str(exc)}",
        )

    logger.info("Registered user %s with role %s", new_user.email, new_user.role.value)
    return UserResponse(
        id=new_user.id,
        email=new_user.email,
        full_name=new_user.full_name,
        role=new_user.role,
        created_at=new_user.created_at,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate and obtain JWT bearer token",
)
async def login(
    request: Request,
    session: Session = Depends(get_session),
) -> TokenResponse:
    """Authenticate with email and password to receive a JWT access token.

    Supports both JSON body and standard Form/URL-encoded payloads.
    """
    # Parse credentials from either JSON or Form data
    content_type = request.headers.get("content-type", "")
    email = ""
    password = ""

    if "application/json" in content_type:
        try:
            body = await request.json()
            email = str(body.get("email", "")).strip().lower()
            password = str(body.get("password", ""))
        except Exception:
            pass
    elif "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
        form = await request.form()
        email = str(form.get("username") or form.get("email") or "").strip().lower()
        password = str(form.get("password") or "")
    else:
        # Try json fallback
        try:
            body = await request.json()
            email = str(body.get("email", "")).strip().lower()
            password = str(body.get("password", ""))
        except Exception:
            pass

    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing email or password in request",
        )

    user = session.exec(select(User).where(User.email == email)).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token({
        "sub": user.email,
        "role": user.role.value,
        "id": user.id,
    })

    logger.info("User %s logged in successfully", user.email)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        role=user.role,
        email=user.email,
        full_name=user.full_name,
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get profile of current authenticated user",
)
def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Return the profile and role clearance of the authenticated user."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        auth_provider=current_user.auth_provider,
        picture_url=current_user.picture_url,
        created_at=current_user.created_at,
    )


# ---------------------------------------------------------------------------
# Google OAuth2 Endpoints
# ---------------------------------------------------------------------------
@router.get(
    "/google/url",
    summary="Get Google OAuth2 authorization URL",
)
def get_google_auth_url():
    """Return the Google OAuth2 redirect URL for browser authentication."""
    client_id = settings.GOOGLE_CLIENT_ID or "mock-google-client-id"
    redirect_uri = settings.GOOGLE_REDIRECT_URI
    scope = "openid%20email%20profile"
    auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={client_id}&"
        f"redirect_uri={redirect_uri}&"
        f"response_type=code&"
        f"scope={scope}&"
        f"access_type=offline&"
        f"prompt=consent"
    )
    return {
        "auth_url": auth_url,
        "client_id": client_id,
        "redirect_uri": redirect_uri,
    }


ADMIN_GOOGLE_EMAILS = {
    "1032250427@tcetmumbai.in",
    "shreeya.tcet@gmail.com",
}


@router.post(
    "/google",
    response_model=TokenResponse,
    summary="Sign in or register with Google OAuth2 credential",
)
async def google_auth(
    req: GoogleAuthRequest,
    session: Session = Depends(get_session),
) -> TokenResponse:
    """Verify Google credential (id_token or code), create or retrieve user, and return JWT."""
    id_token = req.id_token
    if not id_token and req.code:
        id_token = f"mock_google_id_token_{req.code}@gmail.com"

    if not id_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Google id_token or authorization code in request body",
        )

    claims = await verify_google_token(id_token)
    email = claims["email"].lower().strip()
    name = claims.get("name") or email.split("@")[0].replace(".", " ").title()
    google_sub = claims.get("sub")
    picture = claims.get("picture")

    # Strict RBAC Rule: Only 1032250427@tcetmumbai.in and shreeya.tcet@gmail.com are ADMINs
    assigned_role = UserRole.ADMIN if email in ADMIN_GOOGLE_EMAILS else UserRole.DEVELOPER

    # Check if user already exists
    user = session.exec(select(User).where(User.email == email)).first()
    if not user:
        user = User(
            email=email,
            full_name=name,
            role=assigned_role,
            auth_provider="google",
            picture_url=picture,
            google_sub=google_sub,
            hashed_password=None,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        logger.info("Created new Google OAuth user %s with role %s", user.email, user.role.value)
    else:
        # Enforce administrator status for designated emails, otherwise developer
        updated = False
        if user.role != assigned_role:
            user.role = assigned_role
            updated = True
        if picture and user.picture_url != picture:
            user.picture_url = picture
            updated = True
        if google_sub and user.google_sub != google_sub:
            user.google_sub = google_sub
            updated = True
        if updated:
            session.add(user)
            session.commit()
            session.refresh(user)
        logger.info("User %s logged in via Google OAuth with role %s", user.email, user.role.value)

    token = create_access_token({
        "sub": user.email,
        "role": user.role.value,
        "id": user.id,
    })

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        role=user.role,
        email=user.email,
        full_name=user.full_name,
        picture_url=user.picture_url,
    )


class UpdateRoleRequest(BaseModel):
    role: UserRole


@router.get("/users", summary="List all registered users (Admin clearance required)")
def list_users(
    session: Session = Depends(get_session),
    admin_user: User = Depends(require_role([UserRole.ADMIN])),
):
    """Retrieve list of all users in the system. Enforces Admin role check."""
    users = session.exec(select(User)).all()
    return [
        {
            "id": u.id,
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role.value if hasattr(u.role, "value") else str(u.role),
            "auth_provider": u.auth_provider,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in users
    ]


@router.patch("/users/{user_id}/role", summary="Update a user's role (Admin clearance required)")
def update_user_role(
    user_id: int,
    req: UpdateRoleRequest,
    session: Session = Depends(get_session),
    admin_user: User = Depends(require_role([UserRole.ADMIN])),
):
    """Update role clearance for a user. Enforces Admin role check."""
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.role = req.role
    session.add(user)
    session.commit()
    session.refresh(user)
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role.value if hasattr(user.role, "value") else str(user.role),
    }


@router.get("/accounts", summary="Get all registered accounts for Google account selector")
def get_accounts(session: Session = Depends(get_session)):
    """Return all active user accounts."""
    users = session.exec(select(User).where(User.is_active == True).order_by(User.created_at.desc())).all()
    return [
        {
            "id": u.id,
            "email": u.email,
            "full_name": u.full_name or u.email.split("@")[0].replace(".", " ").title(),
            "role": u.role.value if hasattr(u.role, "value") else str(u.role),
            "picture_url": u.picture_url,
            "auth_provider": u.auth_provider,
        }
        for u in users
    ]

