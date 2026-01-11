from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..db import get_db
from ..models import Group, GroupMember, IdentityProvider, RoleBinding, Tenant, User, UserIdentity
from ..rbac import authorize
from ..scim_utils import (
    build_scim_group,
    build_scim_user,
    parse_scim_filter,
    parse_scim_patch,
    SCIM_GROUP_SCHEMAS,
    SCIM_USER_SCHEMAS,
)
from ..sessions import clear_session
from ..tenancy import get_tenant_and_project

router = APIRouter()

SCIM_ENABLED = os.getenv("SCIM_ENABLED", "false").lower() == "true"
SCIM_BEARER_TOKEN = os.getenv("SCIM_BEARER_TOKEN", "")
SCIM_ROLE_MAP_STR = os.getenv("SCIM_ROLE_MAP", "{}")

# Parse role map
try:
    SCIM_ROLE_MAP: dict[str, list[str]] = json.loads(SCIM_ROLE_MAP_STR)
except Exception:
    SCIM_ROLE_MAP = {}


def verify_scim_auth(request: Request) -> None:
    """Verify SCIM bearer token."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing bearer token")
    token = auth_header[7:]
    if token != SCIM_BEARER_TOKEN:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid bearer token")


def sync_user_roles(db: Session, user_id: str, tenant_id: str, groups: list[str]) -> None:
    """Sync role bindings for user based on group membership."""
    # Get user email
    user = db.get(User, user_id)
    if not user:
        return

    # Get current bindings for this user
    existing_bindings = db.scalars(
        select(RoleBinding).where(
            RoleBinding.tenant_id == tenant_id,
            RoleBinding.project_id.is_(None),
            RoleBinding.subject_type == "user",
            RoleBinding.subject_id == user.email,
        )
    ).all()

    # Determine which roles should exist based on groups
    expected_roles: set[str] = set()
    for group_name in groups:
        group_lower = group_name.lower()
        for role, role_groups in SCIM_ROLE_MAP.items():
            for role_group in role_groups:
                if role_group.lower() == group_lower:
                    expected_roles.add(role)

    user = db.get(User, user_id)
    if not user:
        return

    # Remove bindings for roles not in expected set
    for binding in existing_bindings:
        if binding.role not in expected_roles:
            db.delete(binding)

    # Add bindings for new roles
    existing_role_names = {b.role for b in existing_bindings}
    for role in expected_roles:
        if role not in existing_role_names:
            binding = RoleBinding(
                tenant_id=tenant_id,
                project_id=None,
                subject_type="user",
                subject_id=user.email,
                role=role,
            )
            db.add(binding)

    db.flush()

    # Audit log
    write_audit(
        actor_type="system",
        actor_id="scim",
        tenant_id=tenant_id,
        action="scim.roles.sync",
        resource_type="user",
        resource_id=user_id,
        payload={"groups": groups, "roles": list(expected_roles)},
    )


@router.get("/scim/v2/Users")
def list_scim_users(
    request: Request,
    filter: str | None = Query(default=None, alias="filter"),
    startIndex: int = Query(default=1),
    count: int = Query(default=100),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """List SCIM users with optional filtering."""
    verify_scim_auth(request)
    if not SCIM_ENABLED:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="SCIM not enabled")

    tenant_id, _ = get_tenant_and_project(request, db)

    # Get SCIM provider
    scim_provider = db.scalar(select(IdentityProvider).where(IdentityProvider.id == "scim"))
    if not scim_provider:
        return {"schemas": SCIM_USER_SCHEMAS, "totalResults": 0, "itemsPerPage": 0, "startIndex": 1, "Resources": []}

    stmt = select(UserIdentity).where(UserIdentity.provider_id == scim_provider.id)

    # Parse filter
    if filter:
        parsed = parse_scim_filter(filter)
        if parsed and parsed.get("attribute") == "userName":
            stmt = stmt.where(UserIdentity.email == parsed["value"])

    identities = db.scalars(stmt).offset(startIndex - 1).limit(count).all()

    resources = []
    for identity in identities:
        user = db.get(User, identity.user_id)
        if user:
            resources.append(build_scim_user(user, identity.email, identity.external_id))

    return {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "totalResults": len(resources),
        "itemsPerPage": count,
        "startIndex": startIndex,
        "Resources": resources,
    }


@router.post("/scim/v2/Users", status_code=status.HTTP_201_CREATED)
def create_scim_user(
    payload: dict[str, Any],
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Create SCIM user."""
    verify_scim_auth(request)
    if not SCIM_ENABLED:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="SCIM not enabled")

    tenant_id, _ = get_tenant_and_project(request, db)
    email = payload.get("userName") or (payload.get("emails", [{}])[0].get("value") if payload.get("emails") else None)
    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="userName or email required")

    external_id = payload.get("id") or str(uuid4())
    active = payload.get("active", True)

    # Get or create SCIM provider
    scim_provider = db.scalar(select(IdentityProvider).where(IdentityProvider.id == "scim"))
    if not scim_provider:
        scim_provider = IdentityProvider(id="scim", name="SCIM", issuer="scim", client_id="scim")
        db.add(scim_provider)
        db.flush()

    # Find or create user
    user = db.scalar(select(User).where(User.email == email))
    if not user:
        user = User(email=email, password_hash=None, is_disabled=not active)
        db.add(user)
        db.flush()

    # Find or create user identity
    identity = db.scalar(
        select(UserIdentity).where(
            UserIdentity.provider_id == scim_provider.id, UserIdentity.subject == email
        )
    )
    if not identity:
        identity = UserIdentity(
            user_id=user.id,
            provider_id=scim_provider.id,
            subject=email,
            email=email,
            external_id=external_id,
        )
        db.add(identity)
    else:
        identity.external_id = external_id

    user.is_disabled = not active
    db.commit()
    db.refresh(user)
    db.refresh(identity)

    return build_scim_user(user, email, external_id, active)


@router.get("/scim/v2/Users/{user_id}")
def get_scim_user(
    user_id: str,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Get SCIM user by external ID."""
    verify_scim_auth(request)
    if not SCIM_ENABLED:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="SCIM not enabled")

    tenant_id, _ = get_tenant_and_project(request, db)

    scim_provider = db.scalar(select(IdentityProvider).where(IdentityProvider.id == "scim"))
    if not scim_provider:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")

    identity = db.scalar(
        select(UserIdentity).where(
            UserIdentity.provider_id == scim_provider.id,
            UserIdentity.external_id == user_id,
        )
    )
    if not identity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")

    user = db.get(User, identity.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")

    return build_scim_user(user, identity.email, identity.external_id)


@router.put("/scim/v2/Users/{user_id}")
def update_scim_user(
    user_id: str,
    payload: dict[str, Any],
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Update SCIM user (full replace)."""
    verify_scim_auth(request)
    if not SCIM_ENABLED:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="SCIM not enabled")

    tenant_id, _ = get_tenant_and_project(request, db)

    scim_provider = db.scalar(select(IdentityProvider).where(IdentityProvider.id == "scim"))
    if not scim_provider:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")

    identity = db.scalar(
        select(UserIdentity).where(
            UserIdentity.provider_id == scim_provider.id,
            UserIdentity.external_id == user_id,
        )
    )
    if not identity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")

    user = db.get(User, identity.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")

    # Update fields
    active = payload.get("active", True)
    user.is_disabled = not active

    email = payload.get("userName") or identity.email
    if email != identity.email:
        identity.email = email
        user.email = email

    db.commit()
    db.refresh(user)
    db.refresh(identity)

    return build_scim_user(user, identity.email, identity.external_id, active)


@router.patch("/scim/v2/Users/{user_id}")
def patch_scim_user(
    user_id: str,
    payload: dict[str, Any],
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Patch SCIM user (partial update)."""
    verify_scim_auth(request)
    if not SCIM_ENABLED:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="SCIM not enabled")

    tenant_id, _ = get_tenant_and_project(request, db)

    scim_provider = db.scalar(select(IdentityProvider).where(IdentityProvider.id == "scim"))
    if not scim_provider:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")

    identity = db.scalar(
        select(UserIdentity).where(
            UserIdentity.provider_id == scim_provider.id,
            UserIdentity.external_id == user_id,
        )
    )
    if not identity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")

    user = db.get(User, identity.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")

    operations = payload.get("Operations", [])
    parsed = parse_scim_patch(operations)

    # Handle active flag
    if "active" in parsed.get("replace", {}):
        active = parsed["replace"]["active"]
        user.is_disabled = not active
        # Revoke sessions (clear all sessions for this user)
        # TODO: Invalidate session tokens in session store

    db.commit()
    db.refresh(user)
    db.refresh(identity)

    return build_scim_user(user, identity.email, identity.external_id, not user.is_disabled)


@router.delete("/scim/v2/Users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_scim_user(
    user_id: str,
    request: Request,
    db: Session = Depends(get_db),
) -> None:
    """Delete SCIM user (soft delete - disable)."""
    verify_scim_auth(request)
    if not SCIM_ENABLED:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="SCIM not enabled")

    tenant_id, _ = get_tenant_and_project(request, db)

    scim_provider = db.scalar(select(IdentityProvider).where(IdentityProvider.id == "scim"))
    if not scim_provider:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")

    identity = db.scalar(
        select(UserIdentity).where(
            UserIdentity.provider_id == scim_provider.id,
            UserIdentity.external_id == user_id,
        )
    )
    if not identity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")

    user = db.get(User, identity.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")

    # Soft delete: disable user
    user.is_disabled = True
    db.commit()


@router.get("/scim/v2/Groups")
def list_scim_groups(
    request: Request,
    filter: str | None = Query(default=None, alias="filter"),
    startIndex: int = Query(default=1),
    count: int = Query(default=100),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """List SCIM groups."""
    verify_scim_auth(request)
    if not SCIM_ENABLED:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="SCIM not enabled")

    tenant_id, _ = get_tenant_and_project(request, db)

    stmt = select(Group).where(Group.tenant_id == tenant_id)

    # Parse filter
    if filter:
        parsed = parse_scim_filter(filter)
        if parsed and parsed.get("attribute") == "displayName":
            stmt = stmt.where(Group.display_name == parsed["value"])

    groups = db.scalars(stmt).offset(startIndex - 1).limit(count).all()

    resources = []
    for group in groups:
        members = db.scalars(select(GroupMember).where(GroupMember.group_id == group.id)).all()
        member_resources = []
        for member in members:
            user = db.get(User, member.user_id)
            if user:
                scim_provider = db.scalar(select(IdentityProvider).where(IdentityProvider.id == "scim"))
                if scim_provider:
                    identity = db.scalar(
                        select(UserIdentity).where(
                            UserIdentity.user_id == user.id, UserIdentity.provider_id == scim_provider.id
                        )
                    )
                    if identity and identity.external_id:
                        member_resources.append({"value": identity.external_id, "type": "User"})
        resources.append(build_scim_group(group, group.external_id, member_resources))

    return {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "totalResults": len(resources),
        "itemsPerPage": count,
        "startIndex": startIndex,
        "Resources": resources,
    }


@router.post("/scim/v2/Groups", status_code=status.HTTP_201_CREATED)
def create_scim_group(
    payload: dict[str, Any],
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Create SCIM group."""
    verify_scim_auth(request)
    if not SCIM_ENABLED:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="SCIM not enabled")

    tenant_id, _ = get_tenant_and_project(request, db)
    display_name = payload.get("displayName", "")
    if not display_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="displayName required")

    external_id = payload.get("id") or str(uuid4())
    members = payload.get("members", [])

    # Find or create group
    group = db.scalar(
        select(Group).where(Group.tenant_id == tenant_id, Group.display_name == display_name)
    )
    if not group:
        group = Group(tenant_id=tenant_id, display_name=display_name, external_id=external_id)
        db.add(group)
        db.flush()
    else:
        group.external_id = external_id

    # Get SCIM provider
    scim_provider = db.scalar(select(IdentityProvider).where(IdentityProvider.id == "scim"))
    if not scim_provider:
        scim_provider = IdentityProvider(id="scim", name="SCIM", issuer="scim", client_id="scim")
        db.add(scim_provider)
        db.flush()

    # Add members
    for member in members:
        member_id = member.get("value")
        if not member_id:
            continue

        # Find user by external_id (SCIM resource ID)
        identity = db.scalar(
            select(UserIdentity).where(
                UserIdentity.external_id == member_id, UserIdentity.provider_id == scim_provider.id
            )
        )
        if identity:
            # Check if member already exists
            existing = db.scalar(
                select(GroupMember).where(
                    GroupMember.group_id == group.id, GroupMember.user_id == identity.user_id
                )
            )
            if not existing:
                group_member = GroupMember(group_id=group.id, user_id=identity.user_id)
                db.add(group_member)

    db.commit()
    db.refresh(group)

    # Sync roles for all members
    for member in db.scalars(select(GroupMember).where(GroupMember.group_id == group.id)).all():
        user_groups_list = [
            g.display_name
            for g in db.scalars(
                select(Group).join(GroupMember).where(GroupMember.user_id == member.user_id)
            ).all()
        ]
        sync_user_roles(db, member.user_id, tenant_id, user_groups_list)

    member_resources = [
        {"value": m.get("value", ""), "type": "User"} for m in members if m.get("value")
    ]
    return build_scim_group(group, group.external_id, member_resources)


@router.get("/scim/v2/Groups/{group_id}")
def get_scim_group(
    group_id: str,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Get SCIM group by external ID."""
    verify_scim_auth(request)
    if not SCIM_ENABLED:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="SCIM not enabled")

    tenant_id, _ = get_tenant_and_project(request, db)

    group = db.scalar(
        select(Group).where(Group.tenant_id == tenant_id, Group.external_id == group_id)
    )
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="group not found")

    members = db.scalars(select(GroupMember).where(GroupMember.group_id == group.id)).all()
    member_resources = []
    for member in members:
        user = db.get(User, member.user_id)
        if user:
                scim_provider = db.scalar(select(IdentityProvider).where(IdentityProvider.id == "scim"))
                if scim_provider:
                    identity = db.scalar(
                        select(UserIdentity).where(
                            UserIdentity.user_id == user.id, UserIdentity.provider_id == scim_provider.id
                        )
                    )
                else:
                    identity = None
                if identity and identity.external_id:
                    member_resources.append({"value": identity.external_id, "type": "User"})

    return build_scim_group(group, group.external_id, member_resources)


@router.put("/scim/v2/Groups/{group_id}")
def update_scim_group(
    group_id: str,
    payload: dict[str, Any],
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Update SCIM group (full replace)."""
    verify_scim_auth(request)
    if not SCIM_ENABLED:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="SCIM not enabled")

    tenant_id, _ = get_tenant_and_project(request, db)

    group = db.scalar(
        select(Group).where(Group.tenant_id == tenant_id, Group.external_id == group_id)
    )
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="group not found")

    # Update display name
    display_name = payload.get("displayName", "")
    if display_name:
        group.display_name = display_name

    # Replace members
    members = payload.get("members", [])
    # Remove all existing members
    existing_members = db.scalars(select(GroupMember).where(GroupMember.group_id == group.id)).all()
    for member in existing_members:
        db.delete(member)
    # Get SCIM provider
    scim_provider = db.scalar(select(IdentityProvider).where(IdentityProvider.id == "scim"))
    if not scim_provider:
        scim_provider = IdentityProvider(id="scim", name="SCIM", issuer="scim", client_id="scim")
        db.add(scim_provider)
        db.flush()
    # Add new members
    for member in members:
        member_id = member.get("value")
        if not member_id:
            continue
        identity = db.scalar(
            select(UserIdentity).where(
                UserIdentity.external_id == member_id, UserIdentity.provider_id == scim_provider.id
            )
        )
        if identity:
            group_member = GroupMember(group_id=group.id, user_id=identity.user_id)
            db.add(group_member)

    db.commit()
    db.refresh(group)

    # Sync roles for all members
    for member in db.scalars(select(GroupMember).where(GroupMember.group_id == group.id)).all():
        user_groups_list = [
            g.display_name
            for g in db.scalars(
                select(Group).join(GroupMember).where(GroupMember.user_id == member.user_id)
            ).all()
        ]
        sync_user_roles(db, member.user_id, tenant_id, user_groups_list)

    member_resources = [
        {"value": m.get("value", ""), "type": "User"} for m in members if m.get("value")
    ]
    return build_scim_group(group, group.external_id, member_resources)


@router.patch("/scim/v2/Groups/{group_id}")
def patch_scim_group(
    group_id: str,
    payload: dict[str, Any],
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Patch SCIM group (partial update)."""
    verify_scim_auth(request)
    if not SCIM_ENABLED:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="SCIM not enabled")

    tenant_id, _ = get_tenant_and_project(request, db)

    group = db.scalar(
        select(Group).where(Group.tenant_id == tenant_id, Group.external_id == group_id)
    )
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="group not found")

    operations = payload.get("Operations", [])
    parsed = parse_scim_patch(operations)

    # Handle member changes
    if "members" in parsed.get("add", {}):
        for member in parsed["add"]["members"]:
            member_id = member.get("value")
            if not member_id:
                continue
            scim_provider = db.scalar(select(IdentityProvider).where(IdentityProvider.id == "scim"))
            if not scim_provider:
                continue
            identity = db.scalar(
                select(UserIdentity).where(
                    UserIdentity.external_id == member_id, UserIdentity.provider_id == scim_provider.id
                )
            )
            if identity:
                existing = db.scalar(
                    select(GroupMember).where(
                        GroupMember.group_id == group.id, GroupMember.user_id == identity.user_id
                    )
                )
                if not existing:
                    group_member = GroupMember(group_id=group.id, user_id=identity.user_id)
                    db.add(group_member)
                    # Sync roles
                    user_groups_stmt = (
                        select(Group)
                        .join(GroupMember)
                        .where(GroupMember.user_id == identity.user_id, Group.tenant_id == tenant_id)
                    )
                    user_groups_list = [g.display_name for g in db.scalars(user_groups_stmt).all()]
                    sync_user_roles(db, identity.user_id, tenant_id, user_groups_list)

    if "members" in parsed.get("remove", {}):
        for member in parsed["remove"]["members"]:
            member_id = member.get("value")
            if not member_id:
                continue
            scim_provider = db.scalar(select(IdentityProvider).where(IdentityProvider.id == "scim"))
            if not scim_provider:
                continue
            identity = db.scalar(
                select(UserIdentity).where(
                    UserIdentity.external_id == member_id, UserIdentity.provider_id == scim_provider.id
                )
            )
            if identity:
                group_member = db.scalar(
                    select(GroupMember).where(
                        GroupMember.group_id == group.id, GroupMember.user_id == identity.user_id
                    )
                )
                if group_member:
                    db.delete(group_member)
                    # Sync roles
                    user_groups_stmt = (
                        select(Group)
                        .join(GroupMember)
                        .where(GroupMember.user_id == identity.user_id, Group.tenant_id == tenant_id)
                    )
                    user_groups_list = [g.display_name for g in db.scalars(user_groups_stmt).all()]
                    sync_user_roles(db, identity.user_id, tenant_id, user_groups_list)

    db.commit()
    db.refresh(group)

    members = db.scalars(select(GroupMember).where(GroupMember.group_id == group.id)).all()
    member_resources = []
    for member in members:
        user = db.get(User, member.user_id)
        if user:
                scim_provider = db.scalar(select(IdentityProvider).where(IdentityProvider.id == "scim"))
                if scim_provider:
                    identity = db.scalar(
                        select(UserIdentity).where(
                            UserIdentity.user_id == user.id, UserIdentity.provider_id == scim_provider.id
                        )
                    )
                else:
                    identity = None
                if identity and identity.external_id:
                    member_resources.append({"value": identity.external_id, "type": "User"})

    return build_scim_group(group, group.external_id, member_resources)


@router.delete("/scim/v2/Groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_scim_group(
    group_id: str,
    request: Request,
    db: Session = Depends(get_db),
) -> None:
    """Delete SCIM group."""
    verify_scim_auth(request)
    if not SCIM_ENABLED:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="SCIM not enabled")

    tenant_id, _ = get_tenant_and_project(request, db)

    group = db.scalar(
        select(Group).where(Group.tenant_id == tenant_id, Group.external_id == group_id)
    )
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="group not found")

    # Sync roles for all members before deleting
    for member in db.scalars(select(GroupMember).where(GroupMember.group_id == group.id)).all():
        # Get all groups for this user except the one being deleted
        user_groups_stmt = (
            select(Group)
            .join(GroupMember)
            .where(GroupMember.user_id == member.user_id, Group.tenant_id == tenant_id, Group.id != group.id)
        )
        user_groups_list = [g.display_name for g in db.scalars(user_groups_stmt).all()]
        sync_user_roles(db, member.user_id, tenant_id, user_groups_list)

    db.delete(group)
    db.commit()

