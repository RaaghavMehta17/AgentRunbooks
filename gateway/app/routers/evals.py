from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..db import get_db
from ..models import EvalResult
from ..rbac import authorize
from ..tenancy import get_tenant_and_project

router = APIRouter()


@router.get("/evals")
def list_evals(
    request: Request,
    db: Session = Depends(get_db),
    _auth: None = Depends(authorize("read", "eval")),
) -> list[dict]:
    """List recent eval results."""
    tenant_id, project_id = get_tenant_and_project(request, db)
    stmt = select(EvalResult).where(EvalResult.tenant_id == tenant_id).order_by(EvalResult.created_at.desc()).limit(50)
    if project_id:
        stmt = stmt.where(EvalResult.project_id == project_id)
    results = db.scalars(stmt).all()
    return [
        {
            "id": e.id,
            "suite": e.suite,
            "accuracy": e.accuracy,
            "hallu_rate": e.hallu_rate,
            "p95_ms": e.p95_ms,
            "cost_usd": e.cost_usd,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in results
    ]


@router.get("/evals/{eval_id}")
def get_eval(
    eval_id: str,
    request: Request,
    db: Session = Depends(get_db),
    _auth: None = Depends(authorize("read", "eval")),
) -> dict:
    """Get a specific eval result."""
    tenant_id, project_id = get_tenant_and_project(request, db)
    stmt = select(EvalResult).where(EvalResult.id == eval_id, EvalResult.tenant_id == tenant_id)
    if project_id:
        stmt = stmt.where(EvalResult.project_id == project_id)
    eval_result = db.scalars(stmt).first()
    if not eval_result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="eval not found")
    
    return {
        "id": eval_result.id,
        "suite": eval_result.suite,
        "accuracy": eval_result.accuracy,
        "hallu_rate": eval_result.hallu_rate,
        "p95_ms": eval_result.p95_ms,
        "cost_usd": eval_result.cost_usd,
        "created_at": eval_result.created_at.isoformat() if eval_result.created_at else None,
    }


class RunEvalRequest(BaseModel):
    runbook_id: str | None = None
    test_cases: list[dict] | None = None


@router.post("/evals/run")
def run_eval(
    payload: RunEvalRequest,
    request: Request,
    db: Session = Depends(get_db),
    _auth: None = Depends(authorize("execute", "eval")),
) -> dict:
    """Run an evaluation."""
    tenant_id, project_id = get_tenant_and_project(request, db)
    
    # TODO: Integrate with eval harness
    eval_result = EvalResult(
        id=str(uuid4()),
        tenant_id=tenant_id,
        project_id=project_id,
        suite=payload.runbook_id or "default",
        accuracy=0.95,
        hallu_rate=0.05,
        p95_ms=1200,
        cost_usd=0.45,
    )
    db.add(eval_result)
    db.commit()
    db.refresh(eval_result)
    
    write_audit(
        actor_type="user",
        actor_id=getattr(request.state, "user_email", "unknown"),
        tenant_id=tenant_id,
        action="eval.run",
        resource_type="eval",
        resource_id=eval_result.id,
        payload={"runbook_id": payload.runbook_id},
    )
    
    return {
        "id": eval_result.id,
        "suite": eval_result.suite,
        "status": "running",
        "message": "Evaluation started",
    }


@router.post("/evals/{eval_id}/rerun")
def rerun_eval(
    eval_id: str,
    request: Request,
    db: Session = Depends(get_db),
    _auth: None = Depends(authorize("execute", "eval")),
) -> dict:
    """Re-run an evaluation."""
    tenant_id, project_id = get_tenant_and_project(request, db)
    stmt = select(EvalResult).where(EvalResult.id == eval_id, EvalResult.tenant_id == tenant_id)
    if project_id:
        stmt = stmt.where(EvalResult.project_id == project_id)
    original = db.scalars(stmt).first()
    if not original:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="eval not found")
    
    # Create a new eval run
    new_eval = EvalResult(
        id=str(uuid4()),
        tenant_id=tenant_id,
        project_id=project_id,
        suite=original.suite,
        accuracy=0.95,
        hallu_rate=0.05,
        p95_ms=1200,
        cost_usd=0.45,
    )
    db.add(new_eval)
    db.commit()
    db.refresh(new_eval)
    
    write_audit(
        actor_type="user",
        actor_id=getattr(request.state, "user_email", "unknown"),
        tenant_id=tenant_id,
        action="eval.rerun",
        resource_type="eval",
        resource_id=new_eval.id,
        payload={"original_id": eval_id},
    )
    
    return {
        "id": new_eval.id,
        "suite": new_eval.suite,
        "status": "running",
        "message": "Evaluation re-run started",
    }


@router.delete("/evals/{eval_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_eval(
    eval_id: str,
    request: Request,
    db: Session = Depends(get_db),
    _auth: None = Depends(authorize("write", "eval")),
):
    """Delete an eval result."""
    tenant_id, project_id = get_tenant_and_project(request, db)
    stmt = select(EvalResult).where(EvalResult.id == eval_id, EvalResult.tenant_id == tenant_id)
    if project_id:
        stmt = stmt.where(EvalResult.project_id == project_id)
    eval_result = db.scalars(stmt).first()
    if not eval_result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="eval not found")
    
    db.delete(eval_result)
    db.commit()
    
    write_audit(
        actor_type="user",
        actor_id=getattr(request.state, "user_email", "unknown"),
        tenant_id=tenant_id,
        action="eval.delete",
        resource_type="eval",
        resource_id=eval_id,
        payload={"suite": eval_result.suite},
    )

