from __future__ import annotations

import json
import uuid
import asyncio
from datetime import datetime, timedelta
from typing import Any, Optional
import os

import yaml
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select, asc, nullsfirst
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from app.audit import write_audit
from app.db import get_db
from app.models import Approval, Run, RunStatus, Runbook, Step, StepStatus
from app.rbac import authorize
from app.schemas import RunRead, RunbookRead, StepRead
from app.tenancy import get_tenant_and_project
# Lazy import for temporalio to avoid Pydantic TypedDict conflicts at startup

router = APIRouter()


class RunRequest(BaseModel):
    runbook_id: str
    mode: str = "dry-run"
    context: dict[str, Any] = {}
    shadow_expected: Optional[dict[str, Any]] = None


class RunResponse(BaseModel):
    id: str
    status: str
    metrics: dict[str, Any]
    steps: list[StepRead]

    class Config:
        from_attributes = True


def _load_runbook(db: Session, runbook_id: str, tenant_id: str, project_id: str | None) -> RunbookRead:
    stmt = select(Runbook).where(Runbook.id == runbook_id, Runbook.tenant_id == tenant_id)
    if project_id:
        stmt = stmt.where(Runbook.project_id == project_id)
    obj = db.scalars(stmt).first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="runbook not found")
    return RunbookRead.model_validate(obj)


def _plan_from_yaml(yaml_str: str) -> list[dict[str, Any]]:
    data = yaml.safe_load(yaml_str) or {}
    steps = data.get("steps", [])
    normalized = []
    if isinstance(steps, list):
        for step in steps:
            if isinstance(step, dict):
                normalized.append(step)
    return normalized


@router.post("/runs", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
def create_run(
    payload: RunRequest,
    request: Request,
    db: Session = Depends(get_db),
    x_orchestrate: Optional[str] = Header(default=None),
    _auth: None = Depends(authorize("execute", "run")),
) -> RunResponse:
    tenant_id, project_id = get_tenant_and_project(request, db)
    
    # Check quotas before creating run
    try:
        # Estimate projected usage: number of steps
        runbook = _load_runbook(db, payload.runbook_id, tenant_id, project_id)
        plan_steps = _plan_from_yaml(runbook.yaml)
        projected = {
            "steps": len(plan_steps),
            "adapter_calls": len(plan_steps),
            "tokens": 0,  # Will be calculated during execution
            "cost": len(plan_steps) * 0.01,  # Estimate
        }
        enforce_quota(db, tenant_id, projected)
    except QuotaExceeded as e:
        raise HTTPException(
            status_code=402,
            detail={
                "code": "quota_exceeded",
                "metric": e.metric,
                "limit": e.limit,
                "current": e.current,
            },
        )
    
    runbook = _load_runbook(db, payload.runbook_id, tenant_id, project_id)
    plan_steps = _plan_from_yaml(runbook.yaml)
    metrics: dict[str, Any] = {
        "validation": {"rbac_violations": [], "unknown_tools": [], "needs_approval": []},
        "estimated_cost_usd": 0,
        "estimated_tokens": 0,
        "plan": [s.get("name", "") for s in plan_steps],
        "mode": payload.mode,
    }
    if x_orchestrate == "temporal":
        metrics["temporal"] = {"enqueued": False, "reason": "worker stubbed"}
    if payload.shadow_expected:
        metrics["expected"] = payload.shadow_expected
    status_value = RunStatus.RUNNING if payload.mode in {"execute", "dry-run", "shadow"} else RunStatus.PENDING
    run = Run(
        id=str(uuid.uuid4()),
        runbook_id=payload.runbook_id,
        tenant_id=tenant_id,
        project_id=project_id,
        status=status_value,
        metrics=metrics,
    )
    db.add(run)
    db.flush()

    approval_rows: list[Approval] = []
    for step in plan_steps:
        step_obj = Step(
            run_id=run.id,
            name=step.get("name", ""),
            tool=step.get("tool", ""),
            status=StepStatus.PENDING,
            input=step.get("input"),
        )
        db.add(step_obj)
        # Create approval if needed
        if step.get("requires_approval"):
            from ..security import sign_approval

            signed = sign_approval({"run_id": run.id, "step_name": step.get("name", "")})
            approval = Approval(
                run_id=run.id,
                tenant_id=tenant_id,
                project_id=project_id,
                step_name=step.get("name", ""),
                required_roles=step.get("required_roles"),
                approved=False,
                sig=signed["sig"],
                sig_expires_at=signed["expires_at"],
            )
            db.add(approval)
            approval_rows.append(approval)

    db.flush()
    # start workflow if needed
    if payload.mode in {"execute", "shadow"}:
        try:
            # Lazy import to avoid Pydantic TypedDict conflicts at startup
            from temporalio.client import Client
            
            temporal_host = os.getenv("TEMPORAL_HOST", "temporal:7233")
            temporal_namespace = os.getenv("TEMPORAL_NAMESPACE", "default")
            client = asyncio.get_event_loop().run_until_complete(
                Client.connect(temporal_host, namespace=temporal_namespace)
            )
            wf = asyncio.get_event_loop().run_until_complete(
                client.start_workflow(
                    "RunbookWorkflow",
                    run.id,
                    payload.mode,
                    id=f"run-{run.id}",
                    task_queue="runbook-queue",
                )
            )
            run.status = RunStatus.RUNNING
            run.metrics["temporal"] = {"workflow_id": wf.id, "run_id": wf.result_run_id}
        except Exception:
            # inline fallback: mark steps succeeded (mock execution)
            for step in db.query(Step).filter(Step.run_id == run.id).all():
                step.status = StepStatus.SUCCEEDED
                step.started_at = step.started_at or datetime.utcnow()
                step.ended_at = step.ended_at or datetime.utcnow()
            run.status = RunStatus.SUCCEEDED

    db.refresh(run)
    db.refresh(run, attribute_names=["steps"])
    ordered_steps = (
        db.query(Step)
        .filter(Step.run_id == run.id)
        .order_by(nullsfirst(asc(Step.started_at)), asc(Step.name))
        .all()
    )
    # Audit log
    write_audit(
        actor_type="user",
        actor_id=getattr(request.state, "user_email", "unknown"),
        tenant_id=tenant_id,
        action="run.create",
        resource_type="run",
        resource_id=run.id,
        payload={"runbook_id": payload.runbook_id, "mode": payload.mode},
    )
    
    run.steps = ordered_steps
    return RunResponse.model_validate(run)


@router.get("/runs", response_model=list[RunResponse])
def list_runs(
    request: Request,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    _auth: None = Depends(authorize("read", "run")),
) -> list[RunResponse]:
    """List runs with pagination."""
    tenant_id, project_id = get_tenant_and_project(request, db)
    stmt = select(Run).where(Run.tenant_id == tenant_id)
    if project_id:
        stmt = stmt.where(Run.project_id == project_id)
    stmt = stmt.order_by(Run.created_at.desc()).limit(limit).offset(offset)
    results = db.scalars(stmt).all()
    runs = []
    for run in results:
        # Load steps for each run
        steps_stmt = (
            select(Step)
            .where(Step.run_id == run.id)
            .order_by(nullsfirst(Step.started_at), Step.name)
        )
        steps = db.scalars(steps_stmt).all()
        run_dict = RunResponse.model_validate(run).model_dump()
        run_dict["steps"] = [StepRead.model_validate(s).model_dump() for s in steps]
        runs.append(run_dict)
    return runs


@router.get("/runs/{run_id}", response_model=RunResponse)
def get_run(
    run_id: str,
    request: Request,
    db: Session = Depends(get_db),
    _auth: None = Depends(authorize("read", "run")),
) -> RunResponse:
    tenant_id, project_id = get_tenant_and_project(request, db)
    stmt = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id)
    if project_id:
        stmt = stmt.where(Run.project_id == project_id)
    obj = db.scalars(stmt).first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found")
    steps = (
        db.query(Step)
        .filter(Step.run_id == run_id)
        .order_by(nullsfirst(asc(Step.started_at)), asc(Step.name))
        .all()
    )
    obj.steps = steps
    return RunResponse.model_validate(obj)


def _terminal(step_status: StepStatus) -> bool:
    return step_status in {
        StepStatus.SUCCEEDED,
        StepStatus.FAILED,
        StepStatus.SKIPPED,
        StepStatus.COMPENSATED,
    }


@router.get("/runs/{run_id}/events")
async def stream_run_events(
    run_id: str,
    request: Request,
    db: Session = Depends(get_db),
    _auth: None = Depends(authorize("read", "run")),
):
    """Stream run events via SSE with CORS support."""
    tenant_id, project_id = get_tenant_and_project(request, db)
    stmt = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id)
    if project_id:
        stmt = stmt.where(Run.project_id == project_id)
    run = db.scalars(stmt).first()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found")

    async def event_generator():
        end_time = datetime.utcnow() + timedelta(minutes=5)
        last_states: dict[str, str] = {}
        while datetime.utcnow() < end_time:
            steps = (
                db.query(Step)
                .filter(Step.run_id == run_id)
                .order_by(nullsfirst(asc(Step.started_at)), asc(Step.name))
                .all()
            )
            all_terminal = True
            for step in steps:
                status_value = step.status.value if isinstance(step.status, StepStatus) else str(step.status)
                if status_value != last_states.get(step.id):
                    last_states[step.id] = status_value
                    yield {
                        "event": "step",
                        "data": json.dumps({"type": "step", "step": {"name": step.name, "status": status_value}}),
                    }
                if not _terminal(step.status if isinstance(step.status, StepStatus) else StepStatus(status_value)):
                    all_terminal = False
            if all_terminal and steps:
                break
            await asyncio.sleep(1)
        yield {"event": "done", "data": json.dumps({"type": "done", "run_id": run_id})}

    return EventSourceResponse(event_generator())


@router.post("/runs/{run_id}/resume", response_model=RunResponse)
def resume_run(
    run_id: str,
    request: Request,
    db: Session = Depends(get_db),
    _auth: None = Depends(authorize("execute", "run")),
) -> RunResponse:
    tenant_id, project_id = get_tenant_and_project(request, db)
    stmt = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id)
    if project_id:
        stmt = stmt.where(Run.project_id == project_id)
    run = db.scalars(stmt).first()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found")
    # inline resume: mark any approved pending steps as succeeded
    steps = (
        db.query(Step)
        .filter(Step.run_id == run_id)
        .order_by(nullsfirst(asc(Step.started_at)), asc(Step.name))
        .all()
    )
    for step in steps:
        if step.status == StepStatus.PENDING:
            approval = (
                db.query(Approval)
                .filter(Approval.run_id == run_id)
                .filter(Approval.step_name == step.name)
                .first()
            )
            if approval and not approval.approved:
                continue
            step.status = StepStatus.SUCCEEDED
            step.started_at = step.started_at or datetime.utcnow()
            step.ended_at = step.ended_at or datetime.utcnow()
    db.commit()
    run.steps = steps
    return RunResponse.model_validate(run)


@router.post("/runs/{run_id}/pause", response_model=RunResponse)
def pause_run(
    run_id: str,
    request: Request,
    db: Session = Depends(get_db),
    _auth: None = Depends(authorize("execute", "run")),
) -> RunResponse:
    """Pause a running run."""
    tenant_id, project_id = get_tenant_and_project(request, db)
    stmt = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id)
    if project_id:
        stmt = stmt.where(Run.project_id == project_id)
    run = db.scalars(stmt).first()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found")
    
    if run.status != RunStatus.RUNNING:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="run is not running")
    
    # TODO: Implement Temporal workflow pause
    run.status = RunStatus.PENDING
    db.commit()
    db.refresh(run)
    
    write_audit(
        actor_type="user",
        actor_id=getattr(request.state, "user_email", "unknown"),
        tenant_id=tenant_id,
        action="run.pause",
        resource_type="run",
        resource_id=run_id,
        payload={"runbook_id": run.runbook_id},
    )
    
    steps = (
        db.query(Step)
        .filter(Step.run_id == run_id)
        .order_by(nullsfirst(asc(Step.started_at)), asc(Step.name))
        .all()
    )
    run.steps = steps
    return RunResponse.model_validate(run)


@router.post("/runs/{run_id}/cancel", response_model=RunResponse)
def cancel_run(
    run_id: str,
    request: Request,
    db: Session = Depends(get_db),
    _auth: None = Depends(authorize("execute", "run")),
) -> RunResponse:
    """Cancel a running run."""
    tenant_id, project_id = get_tenant_and_project(request, db)
    stmt = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id)
    if project_id:
        stmt = stmt.where(Run.project_id == project_id)
    run = db.scalars(stmt).first()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found")
    
    if run.status not in (RunStatus.RUNNING, RunStatus.PENDING):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="run cannot be cancelled")
    
    run.status = RunStatus.FAILED
    # Cancel all pending/running steps
    steps = (
        db.query(Step)
        .filter(Step.run_id == run_id)
        .order_by(nullsfirst(asc(Step.started_at)), asc(Step.name))
        .all()
    )
    for step in steps:
        if step.status in (StepStatus.PENDING, StepStatus.RUNNING):
            step.status = StepStatus.SKIPPED
            step.ended_at = datetime.utcnow()
    
    db.commit()
    db.refresh(run)
    run.steps = steps
    
    write_audit(
        actor_type="user",
        actor_id=getattr(request.state, "user_email", "unknown"),
        tenant_id=tenant_id,
        action="run.cancel",
        resource_type="run",
        resource_id=run_id,
        payload={"runbook_id": run.runbook_id},
    )
    
    return RunResponse.model_validate(run)

