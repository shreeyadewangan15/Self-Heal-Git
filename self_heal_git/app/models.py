from enum import Enum
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field

def get_utc_now() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(timezone.utc)

class UserRole(str, Enum):
    ADMIN = "ADMIN"
    MAINTAINER = "MAINTAINER"
    DEVELOPER = "DEVELOPER"

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True, nullable=False)
    hashed_password: Optional[str] = Field(default=None, nullable=True)  # Nullable for OAuth accounts
    full_name: str = Field(nullable=False)
    role: UserRole = Field(default=UserRole.DEVELOPER, nullable=False, index=True)
    auth_provider: str = Field(default="local", sa_column_kwargs={"server_default": "local"}, index=True, nullable=False)
    picture_url: Optional[str] = Field(default=None, nullable=True)
    google_sub: Optional[str] = Field(default=None, index=True, nullable=True)
    is_active: bool = Field(default=True, nullable=False)
    created_at: datetime = Field(default_factory=get_utc_now, nullable=False)

class Repository(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    full_name: str = Field(unique=True, index=True, nullable=False)  # e.g. "org/repo"
    webhook_secret: str = Field(nullable=False)
    is_active: bool = Field(default=True, nullable=False)
    auto_commit_enabled: bool = Field(default=True, nullable=False)
    created_by_id: Optional[int] = Field(default=None, foreign_key="user.id", nullable=True)

class PRRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    repo: str = Field(index=True)
    pr_number: int = Field(index=True)
    title: str
    status: str = Field(default="RECEIVED", index=True)
    timestamp: datetime = Field(default_factory=get_utc_now, nullable=False)
    summary: Optional[str] = Field(default=None, nullable=True)
    confidence: Optional[float] = Field(default=None, nullable=True)
    issues_json: Optional[str] = Field(default=None, nullable=True)
    patches_json: Optional[str] = Field(default=None, nullable=True)
    commit_sha: Optional[str] = Field(default=None, nullable=True)

    # RBAC and User Ownership
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", nullable=True)
    repo_id: Optional[int] = Field(default=None, foreign_key="repository.id", nullable=True)
    reviewed_by_id: Optional[int] = Field(default=None, foreign_key="user.id", nullable=True)

# Alias for PRRun to guarantee 100% backward and forward compatibility
PRRun = PRRecord
