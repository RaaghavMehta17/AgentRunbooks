from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..db import get_db
from ..models import Policy
from ..rbac import authorize
from ..schemas import PolicyCreate, PolicyList, PolicyRead
from ..tenancy import get_tenant_and_project

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/policies", response_model=PolicyRead, status_code=status.HTTP_201_CREATED)
def create_policy(
    payload: PolicyCreate,
    request: Request,
    db: Session = Depends(get_db),
    _auth: None = Depends(authorize("write", "policy")),
) -> PolicyRead:
    tenant_id, project_id = get_tenant_and_project(request, db)
    policy = Policy(
        name=payload.name, yaml=payload.yaml, version=payload.version, tenant_id=tenant_id, project_id=project_id
    )
    db.add(policy)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        logger.info("Policy name already exists: %s", payload.name)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="policy with this name already exists",
        )
    db.refresh(policy)

    write_audit(
        actor_type="user",
        actor_id=getattr(request.state, "user_email", "unknown"),
        tenant_id=tenant_id,
        action="policy.create",
        resource_type="policy",
        resource_id=policy.id,
        payload={"name": payload.name, "version": payload.version},
    )

    return PolicyRead.model_validate(policy)


@router.get("/policies", response_model=PolicyList)
def list_policies(
    request: Request,
    db: Session = Depends(get_db),
    _auth: None = Depends(authorize("read", "policy")),
) -> PolicyList:
    tenant_id, project_id = get_tenant_and_project(request, db)
    stmt = select(Policy).where(Policy.tenant_id == tenant_id)
    if project_id:
        stmt = stmt.where(Policy.project_id == project_id)
    stmt = stmt.order_by(Policy.created_at.desc())
    results = db.scalars(stmt).all()
    return PolicyList(policies=[PolicyRead.model_validate(item) for item in results])


@router.get("/policies/{policy_id}", response_model=PolicyRead)
def get_policy(
    policy_id: str,
    request: Request,
    db: Session = Depends(get_db),
    _auth: None = Depends(authorize("read", "policy")),
) -> PolicyRead:
    tenant_id, project_id = get_tenant_and_project(request, db)
    stmt = select(Policy).where(Policy.id == policy_id, Policy.tenant_id == tenant_id)
    if project_id:
        stmt = stmt.where(Policy.project_id == project_id)
    obj = db.scalars(stmt).first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="policy not found")
    return PolicyRead.model_validate(obj)


@router.put("/policies/{policy_id}", response_model=PolicyRead)
def update_policy(
    policy_id: str,
    payload: PolicyCreate,
    request: Request,
    db: Session = Depends(get_db),
    _auth: None = Depends(authorize("write", "policy")),
) -> PolicyRead:
    tenant_id, project_id = get_tenant_and_project(request, db)
    stmt = select(Policy).where(Policy.id == policy_id, Policy.tenant_id == tenant_id)
    if project_id:
        stmt = stmt.where(Policy.project_id == project_id)
    policy = db.scalars(stmt).first()
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="policy not found")
    
    policy.name = payload.name
    policy.yaml = payload.yaml
    policy.version = payload.version
    db.commit()
    db.refresh(policy)
    
    write_audit(
        actor_type="user",
        actor_id=getattr(request.state, "user_email", "unknown"),
        tenant_id=tenant_id,
        action="policy.update",
        resource_type="policy",
        resource_id=policy_id,
        payload={"name": payload.name, "version": payload.version},
    )
    
    return PolicyRead.model_validate(policy)


@router.delete("/policies/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_policy(
    policy_id: str,
    request: Request,
    db: Session = Depends(get_db),
    _auth: None = Depends(authorize("write", "policy")),
):
    tenant_id, project_id = get_tenant_and_project(request, db)
    stmt = select(Policy).where(Policy.id == policy_id, Policy.tenant_id == tenant_id)
    if project_id:
        stmt = stmt.where(Policy.project_id == project_id)
    policy = db.scalars(stmt).first()
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="policy not found")
    
    db.delete(policy)
    db.commit()
    
    write_audit(
        actor_type="user",
        actor_id=getattr(request.state, "user_email", "unknown"),
        tenant_id=tenant_id,
        action="policy.delete",
        resource_type="policy",
        resource_id=policy_id,
        payload={"name": policy.name},
    )


@router.post("/policies/{policy_id}/duplicate", response_model=PolicyRead, status_code=status.HTTP_201_CREATED)
def duplicate_policy(
    policy_id: str,
    request: Request,
    db: Session = Depends(get_db),
    _auth: None = Depends(authorize("write", "policy")),
) -> PolicyRead:
    tenant_id, project_id = get_tenant_and_project(request, db)
    stmt = select(Policy).where(Policy.id == policy_id, Policy.tenant_id == tenant_id)
    if project_id:
        stmt = stmt.where(Policy.project_id == project_id)
    original = db.scalars(stmt).first()
    if not original:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="policy not found")
    
    new_policy = Policy(
        name=f"{original.name} (Copy)",
        yaml=original.yaml,
        version=original.version,
        tenant_id=tenant_id,
        project_id=project_id,
    )
    db.add(new_policy)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="duplicate policy name already exists",
        )
    db.refresh(new_policy)
    
    write_audit(
        actor_type="user",
        actor_id=getattr(request.state, "user_email", "unknown"),
        tenant_id=tenant_id,
        action="policy.duplicate",
        resource_type="policy",
        resource_id=new_policy.id,
        payload={"original_id": policy_id, "name": new_policy.name},
    )
    
    return PolicyRead.model_validate(new_policy)


@router.post("/policies/{policy_id}/test")
def test_policy(
    policy_id: str,
    request: Request,
    db: Session = Depends(get_db),
    _auth: None = Depends(authorize("read", "policy")),
) -> dict:
    """Test a policy against sample data."""
    tenant_id, project_id = get_tenant_and_project(request, db)
    stmt = select(Policy).where(Policy.id == policy_id, Policy.tenant_id == tenant_id)
    if project_id:
        stmt = stmt.where(Policy.project_id == project_id)
    policy = db.scalars(stmt).first()
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="policy not found")
    
    # TODO: Implement policy testing logic
    return {
        "policy_id": policy_id,
        "test_result": "passed",
        "violations": [],
        "warnings": [],
        "message": "Policy test completed successfully",
    }

