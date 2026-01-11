from __future__ import annotations

import os
from typing import Any

from fastapi import Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import SessionLocal
from .models import Project, Tenant

DEFAULT_TENANT_NAME = os.getenv("DEFAULT_TENANT_NAME", "default")
DEFAULT_PROJECT_NAME = os.getenv("DEFAULT_PROJECT_NAME", "default")
AUTO_CREATE_PROJECTS = os.getenv("AUTO_CREATE_PROJECTS", "false").lower() == "true"


def resolve_tenant(request: Request, db: Session) -> str:
    """Resolve tenant_id for request. Returns tenant_id."""
    # 1. From API key (already set in middleware)
    if hasattr(request.state, "tenant_id") and request.state.tenant_id:
        return request.state.tenant_id

    # 2. From JWT/session claim
    if hasattr(request.state, "user_id") and request.state.user_id:
        # Check if tenant_id is in JWT/session (could be added in future)
        # For now, fall through to default
        pass

    # 3. Fallback to default tenant
    tenant = db.scalar(select(Tenant).where(Tenant.name == DEFAULT_TENANT_NAME))
    if not tenant:
        tenant = Tenant(name=DEFAULT_TENANT_NAME)
        db.add(tenant)
        db.flush()

    return tenant.id


def resolve_project(request: Request, db: Session, tenant_id: str) -> str | None:
    """Resolve project_id for request. Returns project_id or None."""
    # Get project name from header
    project_name = request.headers.get("X-Project")
    if not project_name:
        return None

    # Find project
    project = db.scalar(
        select(Project).where(Project.tenant_id == tenant_id, Project.name == project_name)
    )

    if not project:
        if AUTO_CREATE_PROJECTS:
            project = Project(tenant_id=tenant_id, name=project_name)
            db.add(project)
            db.flush()
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"project '{project_name}' not found",
            )

    return project.id


def get_tenant_and_project(request: Request, db: Session) -> tuple[str, str | None]:
    """Resolve tenant_id and project_id for request."""
    tenant_id = resolve_tenant(request, db)
    project_id = resolve_project(request, db, tenant_id)

    # Attach to request state
    request.state.tenant_id = tenant_id
    request.state.project_id = project_id

    return tenant_id, project_id

