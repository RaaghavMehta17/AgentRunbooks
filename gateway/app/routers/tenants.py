from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..db import get_db
from ..models import APIKey, Tenant
from ..security import hash_api_key

router = APIRouter()


class TenantCreate(BaseModel):
    name: str


class TenantRead(BaseModel):
    id: str
    name: str
    created_at: datetime

    class Config:
        from_attributes = True


class APIKeyCreate(BaseModel):
    name: str


class APIKeyRead(BaseModel):
    id: str
    name: str
    created_at: datetime
    last_used_at: datetime | None
    is_active: bool

    class Config:
        from_attributes = True


class APIKeyCreateResponse(BaseModel):
    id: str
    name: str
    plain: str  # One-time plaintext key
    created_at: datetime


@router.post("/tenants", response_model=TenantRead, status_code=status.HTTP_201_CREATED)
def create_tenant(payload: TenantCreate, db: Session = Depends(get_db)) -> TenantRead:
    """Create a new tenant."""
    tenant = Tenant(name=payload.name)
    db.add(tenant)
    try:
        db.flush()
        write_audit(
            actor_type="user",
            actor_id="admin",  # TODO: get from JWT
            tenant_id=None,
            action="tenant.create",
            resource_type="tenant",
            resource_id=tenant.id,
            payload={"name": payload.name},
        )
        db.refresh(tenant)
        return TenantRead.model_validate(tenant)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="tenant name already exists",
        )


@router.post("/tenants/{tenant_id}/apikeys", response_model=APIKeyCreateResponse, status_code=status.HTTP_201_CREATED)
def create_api_key(tenant_id: str, payload: APIKeyCreate, db: Session = Depends(get_db)) -> APIKeyCreateResponse:
    """Create API key for tenant. Returns one-time plaintext key."""
    tenant = db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="tenant not found")

    # Generate key: oka_<random>
    plain_key = f"oka_{secrets.token_urlsafe(32)}"
    hashed = hash_api_key(plain_key)

    api_key = APIKey(
        tenant_id=tenant_id,
        name=payload.name,
        hashed_key=hashed,
    )
    db.add(api_key)
    db.flush()
    write_audit(
        actor_type="user",
        actor_id="admin",
        tenant_id=tenant_id,
        action="apikey.create",
        resource_type="apikey",
        resource_id=api_key.id,
        payload={"name": payload.name},
    )
    db.refresh(api_key)
    return APIKeyCreateResponse(
        id=api_key.id,
        name=api_key.name,
        plain=plain_key,
        created_at=api_key.created_at,
    )


@router.get("/tenants/{tenant_id}/apikeys", response_model=list[APIKeyRead])
def list_api_keys(tenant_id: str, db: Session = Depends(get_db)) -> list[APIKeyRead]:
    """List API keys for tenant (redacted)."""
    tenant = db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="tenant not found")
    stmt = select(APIKey).where(APIKey.tenant_id == tenant_id).order_by(APIKey.created_at.desc())
    keys = db.scalars(stmt).all()
    return [APIKeyRead.model_validate(k) for k in keys]


@router.post("/apikeys/{key_id}/rotate", response_model=APIKeyCreateResponse)
def rotate_api_key(key_id: str, db: Session = Depends(get_db)) -> APIKeyCreateResponse:
    """Rotate API key: deactivate old, create new."""
    old_key = db.get(APIKey, key_id)
    if not old_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="api key not found")
    old_key.is_active = False
    db.flush()

    # Create new key
    plain_key = f"oka_{secrets.token_urlsafe(32)}"
    hashed = hash_api_key(plain_key)
    new_key = APIKey(
        tenant_id=old_key.tenant_id,
        name=f"{old_key.name} (rotated)",
        hashed_key=hashed,
    )
    db.add(new_key)
    db.flush()
    write_audit(
        actor_type="user",
        actor_id="admin",
        tenant_id=old_key.tenant_id,
        action="apikey.rotate",
        resource_type="apikey",
        resource_id=new_key.id,
        payload={"old_key_id": key_id},
    )
    db.refresh(new_key)
    return APIKeyCreateResponse(
        id=new_key.id,
        name=new_key.name,
        plain=plain_key,
        created_at=new_key.created_at,
    )


@router.delete("/apikeys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_api_key(key_id: str, db: Session = Depends(get_db)) -> None:
    """Revoke (deactivate) an API key."""
    api_key = db.get(APIKey, key_id)
    if not api_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="api key not found")
    
    api_key.is_active = False
    db.commit()
    
    write_audit(
        actor_type="user",
        actor_id="admin",
        tenant_id=api_key.tenant_id,
        action="apikey.revoke",
        resource_type="apikey",
        resource_id=key_id,
        payload={"name": api_key.name},
    )

