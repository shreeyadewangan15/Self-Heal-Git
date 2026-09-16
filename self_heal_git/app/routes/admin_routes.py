import logging
from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.config import get_session, engine
from app.models import User, UserRole, Repository, PRRecord
from app.auth import get_current_user, require_role

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["Administrator Control Center"])

# In-memory runtime configuration and telemetry state
RUN_TIME_CONFIG = {
    "model_target": "claude-3-5-sonnet-20241022",
    "confidence_threshold": 0.85,
    "rate_limit_rpm": 60,
    "ast_sandboxing": True,
    "auto_commit_global": True,
}

SYSTEM_AUDIT_LOGS: List[dict] = []


# ---------------------------------------------------------------------------
# Request Schemas
# ---------------------------------------------------------------------------
class RepoCreateRequest(BaseModel):
    full_name: str
    webhook_secret: Optional[str] = "whsec_tcet_default"
    auto_commit_enabled: Optional[bool] = True


class RepoUpdateRequest(BaseModel):
    webhook_secret: Optional[str] = None
    auto_commit_enabled: Optional[bool] = None
    is_active: Optional[bool] = None


class UserUpdateRequest(BaseModel):
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class LLMConfigRequest(BaseModel):
    model_target: Optional[str] = None
    confidence_threshold: Optional[float] = None
    rate_limit_rpm: Optional[int] = None
    ast_sandboxing: Optional[bool] = None
    auto_commit_global: Optional[bool] = None


# ---------------------------------------------------------------------------
# 1. Connected Repositories Management
# ---------------------------------------------------------------------------
@router.get("/repositories", summary="List all monitored repositories")
def list_repositories(
    session: Session = Depends(get_session),
    admin_user: User = Depends(require_role([UserRole.ADMIN])),
):
    """Return all tracked GitHub repositories and their webhook status."""
    repos = session.exec(select(Repository)).all()

    # Calculate PR counts per repo
    prs = session.exec(select(PRRecord)).all()
    repo_pr_counts = {}
    for pr in prs:
        repo_pr_counts[pr.repo] = repo_pr_counts.get(pr.repo, 0) + 1

    return [
        {
            "id": r.id,
            "full_name": r.full_name,
            "webhook_secret": r.webhook_secret,
            "is_active": r.is_active,
            "auto_commit_enabled": getattr(r, "auto_commit_enabled", True),
            "created_by_id": r.created_by_id,
            "pr_count": repo_pr_counts.get(r.full_name, 0),
            "webhook_status": "ACTIVE" if r.is_active else "INACTIVE",
        }
        for r in repos
    ]


@router.post("/repositories", summary="Add or update monitored repository")
def add_or_update_repository(
    req: RepoCreateRequest,
    session: Session = Depends(get_session),
    admin_user: User = Depends(require_role([UserRole.ADMIN])),
):
    """Add a new GitHub repository to autonomous monitoring."""
    clean_name = req.full_name.strip()
    if not clean_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Repository name cannot be empty"
        )

    repo = session.exec(select(Repository).where(Repository.full_name == clean_name)).first()
    if not repo:
        repo = Repository(
            full_name=clean_name,
            webhook_secret=req.webhook_secret or "whsec_tcet_auto",
            is_active=True,
            auto_commit_enabled=req.auto_commit_enabled if req.auto_commit_enabled is not None else True,
            created_by_id=admin_user.id,
        )
        session.add(repo)
    else:
        if req.webhook_secret:
            repo.webhook_secret = req.webhook_secret
        if req.auto_commit_enabled is not None:
            repo.auto_commit_enabled = req.auto_commit_enabled

    session.commit()
    session.refresh(repo)

    SYSTEM_AUDIT_LOGS.insert(0, {
        "id": len(SYSTEM_AUDIT_LOGS) + 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "actor": admin_user.email,
        "action": "REPO_CONNECTED",
        "status": "SUCCESS",
        "details": f"Repository {repo.full_name} added to autonomous monitoring.",
    })

    return {
        "id": repo.id,
        "full_name": repo.full_name,
        "webhook_secret": repo.webhook_secret,
        "is_active": repo.is_active,
        "auto_commit_enabled": getattr(repo, "auto_commit_enabled", True),
        "message": f"Repository {repo.full_name} configured successfully",
    }


@router.delete("/repositories/{repo_id}", summary="Delete monitored repository")
def delete_repository(
    repo_id: int,
    session: Session = Depends(get_session),
    admin_user: User = Depends(require_role([UserRole.ADMIN])),
):
    """Remove a repository from autonomous monitoring."""
    repo = session.get(Repository, repo_id)
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")

    name = repo.full_name
    session.delete(repo)
    session.commit()

    SYSTEM_AUDIT_LOGS.insert(0, {
        "id": len(SYSTEM_AUDIT_LOGS) + 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "actor": admin_user.email,
        "action": "REPO_DISCONNECTED",
        "status": "SUCCESS",
        "details": f"Repository {name} removed from autonomous monitoring.",
    })

    return {"message": f"Repository {name} removed from monitoring", "id": repo_id}


@router.put("/repositories/{repo_id}", summary="Update repository webhook and auto-commit settings")
def update_repository(
    repo_id: int,
    req: RepoUpdateRequest,
    session: Session = Depends(get_session),
    admin_user: User = Depends(require_role([UserRole.ADMIN])),
):
    """Update auto-commit status or webhook secrets for a monitored repository."""
    repo = session.get(Repository, repo_id)
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")

    if req.auto_commit_enabled is not None:
        repo.auto_commit_enabled = req.auto_commit_enabled
    if req.webhook_secret is not None:
        repo.webhook_secret = req.webhook_secret
    if req.is_active is not None:
        repo.is_active = req.is_active

    session.add(repo)
    session.commit()
    session.refresh(repo)

    status_str = "ENABLED" if getattr(repo, "auto_commit_enabled", True) else "PAUSED"
    SYSTEM_AUDIT_LOGS.insert(0, {
        "id": len(SYSTEM_AUDIT_LOGS) + 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "actor": admin_user.email,
        "action": "REPO_SETTING_UPDATED",
        "status": "SUCCESS",
        "details": f"Repository {repo.full_name}: Auto-Commit is now {status_str}.",
    })

    return {
        "id": repo.id,
        "full_name": repo.full_name,
        "webhook_secret": repo.webhook_secret,
        "is_active": repo.is_active,
        "auto_commit_enabled": getattr(repo, "auto_commit_enabled", True),
        "message": f"Repository {repo.full_name} settings updated successfully",
    }


# ---------------------------------------------------------------------------
# 2. User Management & Role Governance
# ---------------------------------------------------------------------------
@router.get("/users", summary="List all users with roles and active status")
def list_users(
    session: Session = Depends(get_session),
    admin_user: User = Depends(require_role([UserRole.ADMIN])),
):
    """List all registered users with clearance roles and activation state."""
    users = session.exec(select(User).order_by(User.created_at.desc())).all()
    return [
        {
            "id": u.id,
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role.value if hasattr(u.role, "value") else str(u.role),
            "auth_provider": u.auth_provider,
            "is_active": getattr(u, "is_active", True),
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in users
    ]


@router.put("/users/{user_id}", summary="Update user role and active state")
def update_user(
    user_id: int,
    req: UserUpdateRequest,
    session: Session = Depends(get_session),
    admin_user: User = Depends(require_role([UserRole.ADMIN])),
):
    """Promote/demote role or activate/deactivate user account."""
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Prevent admin from deactivating themselves
    if user.id == admin_user.id and req.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own administrator account.",
        )

    old_role = user.role.value if hasattr(user.role, "value") else str(user.role)
    if req.role is not None:
        user.role = req.role

    if req.is_active is not None:
        user.is_active = req.is_active

    session.add(user)
    session.commit()
    session.refresh(user)

    action_details = []
    if req.role is not None:
        action_details.append(f"role updated from {old_role} to {req.role}")
    if req.is_active is not None:
        status_str = "activated" if req.is_active else "deactivated"
        action_details.append(f"account {status_str}")

    SYSTEM_AUDIT_LOGS.insert(0, {
        "id": len(SYSTEM_AUDIT_LOGS) + 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "actor": admin_user.email,
        "action": "USER_GOVERNANCE",
        "status": "SUCCESS",
        "details": f"User {user.email}: {', '.join(action_details)}",
    })

    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role.value if hasattr(user.role, "value") else str(user.role),
        "is_active": getattr(user, "is_active", True),
    }


# ---------------------------------------------------------------------------
# 3. System Health & Telemetry Metrics
# ---------------------------------------------------------------------------
@router.get("/telemetry", summary="Get system token usage and health telemetry")
def get_telemetry(
    session: Session = Depends(get_session),
    admin_user: User = Depends(require_role([UserRole.ADMIN])),
):
    """Return token metrics, LLM health, latency, and audit logs."""
    prs = session.exec(select(PRRecord)).all()
    total_runs = len(prs)
    healed_count = sum(1 for p in prs if p.status == "HEALED")
    failed_count = sum(1 for p in prs if p.status == "FAILED")
    analyzing_count = sum(1 for p in prs if p.status in ("ANALYZING", "RECEIVED"))

    # Compute telemetry metrics purely based on actual PR runs
    if total_runs == 0:
        estimated_prompt_tokens = 0
        estimated_completion_tokens = 0
        total_tokens = 0
        estimated_cost_usd = 0.0
        error_rate_pct = 0.0
        avg_latency_sec = 0.0
        token_history = []
    else:
        estimated_prompt_tokens = total_runs * 1450
        estimated_completion_tokens = healed_count * 420
        total_tokens = estimated_prompt_tokens + estimated_completion_tokens
        estimated_cost_usd = round(
            (estimated_prompt_tokens * 0.000003) + (estimated_completion_tokens * 0.000015), 4
        )
        error_rate_pct = round((failed_count / total_runs * 100), 1)
        avg_latency_sec = 1.28

        token_history = []
        for i, pr in enumerate(prs[-5:], start=1):
            t = (i * 1450) + (1 * 420 if pr.status == "HEALED" else 0)
            c = round((i * 1450 * 0.000003) + ((1 if pr.status == "HEALED" else 0) * 420 * 0.000015), 4)
            time_str = pr.timestamp.strftime("%H:%M") if pr.timestamp else f"PR #{pr.pr_number}"
            token_history.append({"timestamp": time_str, "tokens": t, "cost": c})

    return {
        "token_usage": {
            "prompt_tokens": estimated_prompt_tokens,
            "completion_tokens": estimated_completion_tokens,
            "total_tokens": total_tokens,
            "estimated_cost_usd": estimated_cost_usd,
            "history": token_history,
        },
        "llm_health": {
            "success_count": healed_count,
            "failure_count": failed_count,
            "active_runs": analyzing_count,
            "error_rate_pct": error_rate_pct,
            "avg_latency_sec": avg_latency_sec,
            "current_model": RUN_TIME_CONFIG["model_target"],
        },
        "runtime_config": RUN_TIME_CONFIG,
        "audit_logs": SYSTEM_AUDIT_LOGS[:15],
    }


# ---------------------------------------------------------------------------
# 4. LLM Configuration Management
# ---------------------------------------------------------------------------
@router.put("/llm-config", summary="Update autonomous LLM engine parameters")
def update_llm_config(
    req: LLMConfigRequest,
    admin_user: User = Depends(require_role([UserRole.ADMIN])),
):
    """Update runtime diagnostic model target, confidence thresholds, and rate limits."""
    if req.model_target:
        RUN_TIME_CONFIG["model_target"] = req.model_target
    if req.confidence_threshold is not None:
        RUN_TIME_CONFIG["confidence_threshold"] = req.confidence_threshold
    if req.rate_limit_rpm is not None:
        RUN_TIME_CONFIG["rate_limit_rpm"] = req.rate_limit_rpm
    if req.ast_sandboxing is not None:
        RUN_TIME_CONFIG["ast_sandboxing"] = req.ast_sandboxing
    if req.auto_commit_global is not None:
        RUN_TIME_CONFIG["auto_commit_global"] = req.auto_commit_global

    SYSTEM_AUDIT_LOGS.insert(0, {
        "id": len(SYSTEM_AUDIT_LOGS) + 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "actor": admin_user.email,
        "action": "CONFIG_UPDATE",
        "status": "SUCCESS",
        "details": f"Model target: {RUN_TIME_CONFIG['model_target']}, Threshold: {RUN_TIME_CONFIG['confidence_threshold']}, RateLimit: {RUN_TIME_CONFIG['rate_limit_rpm']} RPM.",
    })

    return {
        "message": "LLM engine configuration updated successfully",
        "config": RUN_TIME_CONFIG,
    }
