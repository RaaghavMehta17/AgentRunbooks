from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import SessionLocal
from .models import AuditLog
from .security import hmac_hash


def write_audit(
    actor_type: str,
    actor_id: str,
    tenant_id: str | None,
    action: str,
    resource_type: str,
    resource_id: str | None,
    payload: dict | None = None,
) -> None:
    """Write audit log entry with hash chain."""
    with SessionLocal() as db:
        # Get previous hash for tenant (or None if first)
        prev_hash = None
        if tenant_id:
            stmt = (
                select(AuditLog)
                .where(AuditLog.tenant_id == tenant_id)
                .order_by(AuditLog.ts.desc())
                .limit(1)
            )
            prev = db.scalars(stmt).first()
            if prev:
                prev_hash = prev.hash

        record = {
            "actor_type": actor_type,
            "actor_id": actor_id,
            "tenant_id": tenant_id,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "payload": payload,
        }
        hash_value = hmac_hash(prev_hash, record)

        audit_entry = AuditLog(
            actor_type=actor_type,
            actor_id=actor_id,
            tenant_id=tenant_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            payload=payload,
            prev_hash=prev_hash,
            hash=hash_value,
        )
        db.add(audit_entry)
        db.commit()

