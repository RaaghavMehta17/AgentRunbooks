"""Settings API endpoints for user profile, notifications, security, etc."""

from __future__ import annotations

from typing import Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import User, Tenant
from ..rbac import authorize
from ..tenancy import get_tenant_and_project
from ..security import hash_password, verify_password

router = APIRouter(prefix="/settings", tags=["settings"])


class UserProfileUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    timezone: Optional[str] = None


class PasswordUpdate(BaseModel):
    current_password: str
    new_password: str


class NotificationSettings(BaseModel):
    run_completions_email: bool = True
    run_completions_slack: bool = True
    run_failures_email: bool = True
    run_failures_slack: bool = True
    approval_requests_email: bool = True
    approval_requests_slack: bool = True
    policy_triggers_email: bool = False
    policy_triggers_slack: bool = True
    weekly_reports_email: bool = True
    weekly_reports_slack: bool = False


class DataRetentionSettings(BaseModel):
    run_history_retention_days: int = 90
    audit_log_retention_days: int = 365


@router.get("/profile")
async def get_profile(
    request: Request,
    db: Session = Depends(get_db),
    _auth: None = Depends(authorize("read", "*")),
):
    """Get current user profile."""
    # Get user from request state (set by auth middleware)
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    tenant_id, _ = get_tenant_and_project(request, db)
    tenant = db.get(Tenant, tenant_id) if tenant_id else None
    
    return {
        "id": user.id,
        "email": user.email,
        "name": user.email.split("@")[0].replace(".", " ").title(),  # Derive from email
        "role": "admin",  # TODO: Get from role bindings
        "timezone": "UTC",
        "tenant": {
            "id": tenant.id if tenant else None,
            "name": tenant.name if tenant else "Default",
            "slug": tenant.name.lower().replace(" ", "-") if tenant else "default",
        } if tenant else None,
    }


@router.put("/profile")
async def update_profile(
    payload: UserProfileUpdate,
    request: Request,
    db: Session = Depends(get_db),
    _auth: None = Depends(authorize("write", "*")),
):
    """Update user profile."""
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    if payload.email and payload.email != user.email:
        # Check if email already exists
        existing = db.scalar(select(User).where(User.email == payload.email))
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already in use")
        user.email = payload.email
    
    db.commit()
    return {"message": "Profile updated successfully"}


@router.put("/password")
async def update_password(
    payload: PasswordUpdate,
    request: Request,
    db: Session = Depends(get_db),
    _auth: None = Depends(authorize("write", "*")),
):
    """Update user password."""
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    if not user.password_hash:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password not set (OIDC user)")
    
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Current password incorrect")
    
    user.password_hash = hash_password(payload.new_password)
    db.commit()
    
    return {"message": "Password updated successfully"}


@router.get("/notifications")
async def get_notification_settings(
    request: Request,
    db: Session = Depends(get_db),
    _auth: None = Depends(authorize("read", "*")),
):
    """Get notification settings."""
    return {
        "run_completions_email": True,
        "run_completions_slack": True,
        "run_failures_email": True,
        "run_failures_slack": True,
        "approval_requests_email": True,
        "approval_requests_slack": True,
        "policy_triggers_email": False,
        "policy_triggers_slack": True,
        "weekly_reports_email": True,
        "weekly_reports_slack": False,
    }


@router.put("/notifications")
async def update_notification_settings(
    payload: NotificationSettings,
    request: Request,
    db: Session = Depends(get_db),
    _auth: None = Depends(authorize("write", "*")),
):
    """Update notification settings."""
    # TODO: Persist settings to DB
    return {"message": "Notification settings updated successfully"}


@router.get("/data-retention")
async def get_data_retention_settings(
    request: Request,
    db: Session = Depends(get_db),
    _auth: None = Depends(authorize("read", "*")),
):
    """Get data retention settings."""
    tenant_id, _ = get_tenant_and_project(request, db)
    return {
        "run_history_retention_days": 90,
        "audit_log_retention_days": 365,
    }


@router.put("/data-retention")
async def update_data_retention_settings(
    payload: DataRetentionSettings,
    request: Request,
    db: Session = Depends(get_db),
    _auth: None = Depends(authorize("write", "*")),
):
    """Update data retention settings."""
    tenant_id, _ = get_tenant_and_project(request, db)
    # TODO: Persist retention settings
    return {"message": "Data retention settings updated successfully"}


@router.get("/sessions")
async def get_active_sessions(
    request: Request,
    db: Session = Depends(get_db),
    _auth: None = Depends(authorize("read", "*")),
):
    """Get active sessions for current user."""
    # TODO: Track sessions in DB
    return {
        "sessions": [
            {
                "id": "session-1",
                "device": "Chrome on macOS",
                "location": "San Francisco, CA",
                "lastActive": datetime.now(timezone.utc).isoformat(),
                "current": True,
            },
            {
                "id": "session-2",
                "device": "Safari on iPhone",
                "location": "San Francisco, CA",
                "lastActive": (datetime.now(timezone.utc).replace(hour=datetime.now().hour - 2)).isoformat(),
                "current": False,
            },
        ]
    }


@router.delete("/sessions/{session_id}")
async def revoke_session(
    session_id: str,
    request: Request,
    db: Session = Depends(get_db),
    _auth: None = Depends(authorize("write", "*")),
):
    """Revoke a session."""
    # TODO: Mark session as revoked in DB
    return {"message": "Session revoked successfully"}


@router.get("/webhooks")
async def get_webhooks(
    request: Request,
    db: Session = Depends(get_db),
    _auth: None = Depends(authorize("read", "*")),
):
    """Get webhook configurations."""
    tenant_id, _ = get_tenant_and_project(request, db)
    # TODO: Fetch webhooks from DB
    return {
        "webhooks": [
            {
                "id": "webhook-1",
                "url": "https://your-server.com/webhook",
                "events": ["run.started", "run.completed", "run.failed", "approval.requested"],
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        ]
    }


@router.post("/webhooks")
async def create_webhook(
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    _auth: None = Depends(authorize("write", "*")),
):
    """Create a webhook."""
    tenant_id, _ = get_tenant_and_project(request, db)
    # TODO: Store webhooks in DB
    return {
        "id": "webhook-new",
        "url": payload.get("url"),
        "events": payload.get("events", []),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

