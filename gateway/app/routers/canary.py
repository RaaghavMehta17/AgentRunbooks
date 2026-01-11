from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..db import get_db
from ..models import CanaryPolicy, Run

router = APIRouter()


class CanaryPolicyCreate(BaseModel):
    name: str
    thresholds: dict


class CanaryPolicyRead(BaseModel):
    id: str
    name: str
    thresholds: dict
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class CanaryCheckResponse(BaseModel):
    eligible: bool
    reasons: list[str]


@router.post("/canary/policies", response_model=CanaryPolicyRead, status_code=status.HTTP_201_CREATED)
def create_canary_policy(
    payload: CanaryPolicyCreate, request: Request, db: Session = Depends(get_db)
) -> CanaryPolicyRead:
    """Create or update canary policy with thresholds."""
    stmt = select(CanaryPolicy).where(CanaryPolicy.name == payload.name)
    existing = db.scalars(stmt).first()

    if existing:
        existing.thresholds = payload.thresholds
        db.commit()
        db.refresh(existing)
        write_audit(
            actor_type="user",
            actor_id="admin",
            tenant_id=getattr(request.state, "tenant_id", "default"),
            action="canary.policy.update",
            resource_type="canary_policy",
            resource_id=existing.id,
            payload={"name": payload.name, "thresholds": payload.thresholds},
        )
        return CanaryPolicyRead.model_validate(existing)
    else:
        policy = CanaryPolicy(name=payload.name, thresholds=payload.thresholds)
        db.add(policy)
        db.flush()
        write_audit(
            actor_type="user",
            actor_id="admin",
            tenant_id=getattr(request.state, "tenant_id", "default"),
            action="canary.policy.create",
            resource_type="canary_policy",
            resource_id=policy.id,
            payload={"name": payload.name, "thresholds": payload.thresholds},
        )
        db.refresh(policy)
        return CanaryPolicyRead.model_validate(policy)


@router.get("/canary/check", response_model=CanaryCheckResponse)
def check_canary_eligibility(
    run_id: str = Query(...),
    policy: str = Query("default"),
    db: Session = Depends(get_db),
) -> CanaryCheckResponse:
    """Check if a shadow run meets canary promotion thresholds."""
    run = db.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found")

    shadow_metrics = run.metrics.get("shadow", {})
    if not shadow_metrics.get("enabled"):
        return CanaryCheckResponse(eligible=False, reasons=["not a shadow run"])

    # Load canary policy
    stmt = select(CanaryPolicy).where(CanaryPolicy.name == policy)
    canary_policy = db.scalars(stmt).first()
    if not canary_policy:
        return CanaryCheckResponse(eligible=False, reasons=[f"canary policy '{policy}' not found"])

    thresholds = canary_policy.thresholds
    reasons: list[str] = []

    # Check match score
    match_score = shadow_metrics.get("match_score", 0.0)
    min_match = thresholds.get("min_match_score", 0.0)
    if match_score < min_match:
        reasons.append(f"match_score {match_score:.2f} < {min_match}")

    # Check policy violations
    violations = shadow_metrics.get("policy_violations", 0)
    max_violations = thresholds.get("max_policy_violations", 0)
    if violations > max_violations:
        reasons.append(f"policy_violations {violations} > {max_violations}")

    # Check cost
    cost_usd = run.metrics.get("cost_usd", 0.0)
    max_cost = thresholds.get("max_cost_usd", float("inf"))
    if cost_usd > max_cost:
        reasons.append(f"cost_usd {cost_usd:.2f} > {max_cost}")

    # Check p95 latency
    p95_ms = run.metrics.get("p95_ms", 0.0)
    max_p95 = thresholds.get("max_p95_ms", float("inf"))
    if p95_ms > max_p95:
        reasons.append(f"p95_ms {p95_ms:.0f} > {max_p95}")

    eligible = len(reasons) == 0
    return CanaryCheckResponse(eligible=eligible, reasons=reasons)


@router.post("/runs/{run_id}/promote")
def promote_run(run_id: str, request: Request, db: Session = Depends(get_db)) -> dict:
    """Promote a shadow run to active if it meets canary thresholds."""
    run = db.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found")

    # Check eligibility
    check = check_canary_eligibility(run_id=run_id, policy="default", db=db)
    if not check.eligible:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"not eligible for promotion: {', '.join(check.reasons)}",
        )

    # Mark runbook as promoted
    from ..models import Runbook

    runbook = db.get(Runbook, run.runbook_id)
    if runbook:
        runbook.canary_promoted = True
        db.commit()

        write_audit(
            actor_type="user",
            actor_id="admin",
            tenant_id=getattr(request.state, "tenant_id", "default"),
            action="run.promote",
            resource_type="run",
            resource_id=run_id,
            payload={"runbook_id": run.runbook_id, "match_score": run.metrics.get("shadow", {}).get("match_score")},
        )

    return {"ok": True, "run_id": run_id, "runbook_id": run.runbook_id, "promoted": True}

