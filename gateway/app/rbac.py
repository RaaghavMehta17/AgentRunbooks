from __future__ import annotations

from typing import Any

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import get_db
from .models import RoleBinding
from .sessions import get_session
from .tenancy import get_tenant_and_project

# Permission matrix: role -> (action, resource) -> allowed
PERMISSIONS: dict[str, dict[tuple[str, str], bool]] = {
    "Admin": {
        ("*", "*"): True,  # Admin can do everything
        ("write", "project"): True,
        ("write", "role_binding"): True,
        ("read", "project"): True,
        ("read", "role_binding"): True,
    },
    "SRE": {
        ("write", "runbook"): True,
        ("write", "policy"): True,
        ("read", "runbook"): True,
        ("read", "policy"): True,
        ("read", "run"): True,
        ("execute", "run"): True,
        ("approve", "approval"): False,  # Only if also OnCall
        ("read", "project"): True,
    },
    "OnCall": {
        ("read", "*"): True,
        ("approve", "approval"): True,
    },
    "Viewer": {
        ("read", "*"): True,
    },
}


def _check_permission(role: str, action: str, resource: str) -> bool:
    """Check if role has permission for action on resource."""
    # Admin has all permissions
    if role == "Admin":
        return True

    role_perms = PERMISSIONS.get(role, {})

    # Check exact match
    if (action, resource) in role_perms:
        return role_perms[(action, resource)]

    # Check wildcard action
    if ("*", resource) in role_perms:
        return role_perms[("*", resource)]

    # Check wildcard resource
    if (action, "*") in role_perms:
        return role_perms[(action, "*")]

    # Check wildcard both
    if ("*", "*") in role_perms:
        return role_perms[("*", "*")]

    return False


def _get_subject_identifiers(request: Request) -> list[tuple[str, str]]:
    """Get subject identifiers from request (user, groups, apikey)."""
    subjects: list[tuple[str, str]] = []

    # User from JWT/session
    if hasattr(request.state, "user_email") and request.state.user_email:
        subjects.append(("user", request.state.user_email))

    # Groups from session/JWT (if available)
    if hasattr(request.state, "user_groups") and request.state.user_groups:
        for group in request.state.user_groups:
            subjects.append(("group", group))

    # API key
    if hasattr(request.state, "authn") and request.state.authn == "apikey":
        api_key_id = getattr(request.state, "api_key_id", None)
        if api_key_id:
            subjects.append(("apikey", api_key_id))

    return subjects


def authorize(action: str, resource: str):
    """Dependency to authorize action on resource."""

    def _authorize(
        request: Request,
        db: Session = Depends(get_db),
    ) -> None:
        # Resolve tenant and project
        tenant_id, project_id = get_tenant_and_project(request, db)

        # Get subject identifiers
        subjects = _get_subject_identifiers(request)

        if not subjects:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="authentication required"
            )

        # Look up role bindings
        allowed = False
        roles_checked: set[str] = set()

        for subject_type, subject_id in subjects:
            # Try project-level binding first
            if project_id:
                stmt = select(RoleBinding).where(
                    RoleBinding.tenant_id == tenant_id,
                    RoleBinding.project_id == project_id,
                    RoleBinding.subject_type == subject_type,
                    RoleBinding.subject_id == subject_id,
                )
                bindings = db.scalars(stmt).all()
                for binding in bindings:
                    if binding.role not in roles_checked:
                        roles_checked.add(binding.role)
                        if _check_permission(binding.role, action, resource):
                            allowed = True
                            break

            # Fall back to tenant-level binding
            if not allowed:
                stmt = select(RoleBinding).where(
                    RoleBinding.tenant_id == tenant_id,
                    RoleBinding.project_id.is_(None),
                    RoleBinding.subject_type == subject_type,
                    RoleBinding.subject_id == subject_id,
                )
                bindings = db.scalars(stmt).all()
                for binding in bindings:
                    if binding.role not in roles_checked:
                        roles_checked.add(binding.role)
                        if _check_permission(binding.role, action, resource):
                            allowed = True
                            break

            if allowed:
                break

        # Special case: SRE can approve if also OnCall
        if action == "approve" and resource == "approval":
            has_sre = "SRE" in roles_checked
            has_oncall = "OnCall" in roles_checked
            if has_sre and has_oncall:
                allowed = True

        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"permission denied: {action} on {resource}",
            )

    return _authorize

