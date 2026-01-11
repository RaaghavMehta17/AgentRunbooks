from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..db import get_db
from ..models import Approval, Run, RunStatus, Step, StepStatus
from ..rbac import authorize
from ..security import verify_approval
from ..tenancy import get_tenant_and_project

router = APIRouter()


class ApproveRequest(BaseModel):
    token: str | None = None


@router.get("/approvals")
def list_approvals(
    request: Request,
    db: Session = Depends(get_db),
    _auth: None = Depends(authorize("read", "approval")),
) -> list[dict]:
    """List all approvals."""
    tenant_id, project_id = get_tenant_and_project(request, db)
    stmt = select(Approval).where(Approval.tenant_id == tenant_id)
    if project_id:
        stmt = stmt.where(Approval.project_id == project_id)
    stmt = stmt.order_by(Approval.created_at.desc())
    results = db.scalars(stmt).all()
    return [
        {
            "id": a.id,
            "run_id": a.run_id,
            "step_name": a.step_name,
            "required_roles": a.required_roles,
            "approved": a.approved,
            "token": a.token,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in results
    ]


@router.post("/approvals/{approval_id}/approve")
def approve_approval(
    approval_id: str,
    payload: ApproveRequest,
    request: Request,
    db: Session = Depends(get_db),
    _auth: None = Depends(authorize("approve", "approval")),
) -> dict:
    """Approve an approval request with signed token verification."""
    tenant_id, project_id = get_tenant_and_project(request, db)
    stmt = select(Approval).where(Approval.id == approval_id, Approval.tenant_id == tenant_id)
    if project_id:
        stmt = stmt.where(Approval.project_id == project_id)
    approval = db.scalars(stmt).first()
    if not approval:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="approval not found")
    if approval.approved:
        return {"ok": True, "message": "already approved"}

    # Verify signed token
    if approval.sig and approval.sig_expires_at:
        if not payload.token:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="token required")
        if not verify_approval(payload.token, approval.sig, approval.sig_expires_at):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="invalid or expired token")
    elif approval.token and approval.token != payload.token:
        # Fallback for legacy tokens
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="invalid token")

    approval.approved = True
    db.commit()

    # Audit log
    write_audit(
        actor_type="user",
        actor_id=getattr(request.state, "user_email", "unknown"),
        tenant_id=tenant_id,
        action="approval.approved",
        resource_type="approval",
        resource_id=approval_id,
        payload={"run_id": approval.run_id, "step_name": approval.step_name},
    )

    return {"ok": True, "approval_id": approval_id}


@router.post("/approvals/{approval_id}/deny")
def deny_approval(
    approval_id: str,
    payload: ApproveRequest,
    request: Request,
    db: Session = Depends(get_db),
    _auth: None = Depends(authorize("approve", "approval")),
) -> dict:
    """Deny/reject an approval request."""
    tenant_id, project_id = get_tenant_and_project(request, db)
    stmt = select(Approval).where(Approval.id == approval_id, Approval.tenant_id == tenant_id)
    if project_id:
        stmt = stmt.where(Approval.project_id == project_id)
    approval = db.scalars(stmt).first()
    if not approval:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="approval not found")
    if approval.approved:
        return {"ok": True, "message": "already approved, cannot deny"}
    
    # Mark as denied by setting approved to False (or you could add a denied field)
    # TODO: Add denied status instead of deleting
    run_id = approval.run_id
    step_name = approval.step_name
    db.delete(approval)
    db.commit()
    
    # Cancel the associated run step
    from ..models import Run, Step, StepStatus
    run = db.scalar(select(Run).where(Run.id == run_id))
    if run:
        step = db.scalar(select(Step).where(Step.run_id == run_id, Step.name == step_name))
        if step:
            step.status = StepStatus.FAILED
            step.error = {"message": "Approval denied"}
            step.ended_at = datetime.utcnow()
            run.status = RunStatus.FAILED
            db.commit()
    
    # Audit log
    write_audit(
        actor_type="user",
        actor_id=getattr(request.state, "user_email", "unknown"),
        tenant_id=tenant_id,
        action="approval.reject",
        resource_type="approval",
        resource_id=approval_id,
        payload={"run_id": run_id, "step_name": step_name},
    )
    
    return {"ok": True, "approval_id": approval_id, "message": "approval denied"}

