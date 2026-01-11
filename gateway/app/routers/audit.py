from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import AuditLog
from ..security import hmac_hash
from ..rbac import authorize
from ..tenancy import get_tenant_and_project

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/")
async def list_audit_logs(
    request: Request,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    actor_type: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _auth: None = Depends(authorize("read", "*")),
):
    """List audit logs with filtering."""
    tenant_id, project_id = get_tenant_and_project(request, db)
    
    # Build query
    filters = []
    if tenant_id:
        filters.append(AuditLog.tenant_id == tenant_id)
    if actor_type:
        filters.append(AuditLog.actor_type == actor_type)
    if resource_type:
        filters.append(AuditLog.resource_type == resource_type)
    if action:
        filters.append(AuditLog.action == action)
    
    stmt = select(AuditLog)
    if filters:
        stmt = stmt.where(and_(*filters))
    stmt = stmt.order_by(AuditLog.ts.desc()).limit(limit).offset(offset)
    
    logs = db.scalars(stmt).all()
    
    # Format response
    events = []
    for log in logs:
        # Extract details from payload
        details = ""
        if log.payload:
            if isinstance(log.payload, dict):
                details = str(log.payload.get("details", "")) or str(log.payload)
            else:
                details = str(log.payload)
        
        events.append({
            "id": log.id,
            "timestamp": log.ts.isoformat(),
            "actor": log.actor_id,
            "actorType": log.actor_type,
            "action": log.action,
            "resource": log.resource_id or "",
            "resourceType": log.resource_type,
            "details": details,
            "status": "success",  # Default, could be derived from payload
            "ipAddress": log.payload.get("ip_address") if isinstance(log.payload, dict) else None,
            "userAgent": log.payload.get("user_agent") if isinstance(log.payload, dict) else None,
        })
    
    total = db.query(AuditLog).filter(and_(*filters) if filters else True).count()
    
    return {
        "events": events,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/verify")
def verify_audit_chain(tenant_id: str | None = None, db: Session = Depends(get_db)) -> dict:
    """Verify audit log hash chain integrity."""
    if tenant_id:
        stmt = select(AuditLog).where(AuditLog.tenant_id == tenant_id).order_by(AuditLog.ts.asc())
    else:
        stmt = select(AuditLog).order_by(AuditLog.ts.asc())
    
    logs = db.scalars(stmt).all()
    prev_hash = None
    
    for idx, log in enumerate(logs):
        record = {
            "actor_type": log.actor_type,
            "actor_id": log.actor_id,
            "tenant_id": log.tenant_id,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "payload": log.payload,
        }
        expected_hash = hmac_hash(prev_hash, record)
        
        if log.hash != expected_hash:
            return {
                "ok": False,
                "broken_at": idx,
                "log_id": log.id,
                "expected_hash": expected_hash,
                "actual_hash": log.hash,
            }
        
        prev_hash = log.hash
    
    return {"ok": True, "verified_count": len(logs)}

