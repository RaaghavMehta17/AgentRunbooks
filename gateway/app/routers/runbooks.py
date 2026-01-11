from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..db import get_db
from ..models import Runbook
from ..rbac import authorize
from ..schemas import RunbookCreate, RunbookList, RunbookRead
from ..tenancy import get_tenant_and_project

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/runbooks", response_model=RunbookRead, status_code=status.HTTP_201_CREATED)
def create_runbook(
    payload: RunbookCreate,
    request: Request,
    db: Session = Depends(get_db),
    _auth: None = Depends(authorize("write", "runbook")),
) -> RunbookRead:
    tenant_id, project_id = get_tenant_and_project(request, db)
    runbook = Runbook(name=payload.name, yaml=payload.yaml, tenant_id=tenant_id, project_id=project_id)
    db.add(runbook)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        logger.info("Runbook name already exists: %s", payload.name)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="runbook with this name already exists",
        )
    db.refresh(runbook)

    write_audit(
        actor_type="user",
        actor_id=getattr(request.state, "user_email", "unknown"),
        tenant_id=tenant_id,
        action="runbook.create",
        resource_type="runbook",
        resource_id=runbook.id,
        payload={"name": payload.name},
    )

    return RunbookRead.model_validate(runbook)


@router.get("/runbooks", response_model=RunbookList)
def list_runbooks(
    request: Request,
    db: Session = Depends(get_db),
    _auth: None = Depends(authorize("read", "runbook")),
) -> RunbookList:
    tenant_id, project_id = get_tenant_and_project(request, db)
    stmt = select(Runbook).where(Runbook.tenant_id == tenant_id)
    if project_id:
        stmt = stmt.where(Runbook.project_id == project_id)
    stmt = stmt.order_by(Runbook.created_at.desc())
    results = db.scalars(stmt).all()
    return RunbookList(runbooks=[RunbookRead.model_validate(item) for item in results])


@router.get("/runbooks/{runbook_id}", response_model=RunbookRead)
def get_runbook(
    runbook_id: str,
    request: Request,
    db: Session = Depends(get_db),
    _auth: None = Depends(authorize("read", "runbook")),
) -> RunbookRead:
    tenant_id, project_id = get_tenant_and_project(request, db)
    stmt = select(Runbook).where(Runbook.id == runbook_id, Runbook.tenant_id == tenant_id)
    if project_id:
        stmt = stmt.where(Runbook.project_id == project_id)
    obj = db.scalars(stmt).first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="runbook not found")
    return RunbookRead.model_validate(obj)


@router.put("/runbooks/{runbook_id}", response_model=RunbookRead)
def update_runbook(
    runbook_id: str,
    payload: RunbookCreate,
    request: Request,
    db: Session = Depends(get_db),
    _auth: None = Depends(authorize("write", "runbook")),
) -> RunbookRead:
    tenant_id, project_id = get_tenant_and_project(request, db)
    stmt = select(Runbook).where(Runbook.id == runbook_id, Runbook.tenant_id == tenant_id)
    if project_id:
        stmt = stmt.where(Runbook.project_id == project_id)
    runbook = db.scalars(stmt).first()
    if not runbook:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="runbook not found")
    
    runbook.name = payload.name
    runbook.yaml = payload.yaml
    db.commit()
    db.refresh(runbook)
    
    write_audit(
        actor_type="user",
        actor_id=getattr(request.state, "user_email", "unknown"),
        tenant_id=tenant_id,
        action="runbook.update",
        resource_type="runbook",
        resource_id=runbook_id,
        payload={"name": payload.name},
    )
    
    return RunbookRead.model_validate(runbook)


@router.delete("/runbooks/{runbook_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_runbook(
    runbook_id: str,
    request: Request,
    db: Session = Depends(get_db),
    _auth: None = Depends(authorize("write", "runbook")),
):
    tenant_id, project_id = get_tenant_and_project(request, db)
    stmt = select(Runbook).where(Runbook.id == runbook_id, Runbook.tenant_id == tenant_id)
    if project_id:
        stmt = stmt.where(Runbook.project_id == project_id)
    runbook = db.scalars(stmt).first()
    if not runbook:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="runbook not found")
    
    db.delete(runbook)
    db.commit()
    
    write_audit(
        actor_type="user",
        actor_id=getattr(request.state, "user_email", "unknown"),
        tenant_id=tenant_id,
        action="runbook.delete",
        resource_type="runbook",
        resource_id=runbook_id,
        payload={"name": runbook.name},
    )


@router.post("/runbooks/{runbook_id}/duplicate", response_model=RunbookRead, status_code=status.HTTP_201_CREATED)
def duplicate_runbook(
    runbook_id: str,
    request: Request,
    db: Session = Depends(get_db),
    _auth: None = Depends(authorize("write", "runbook")),
) -> RunbookRead:
    tenant_id, project_id = get_tenant_and_project(request, db)
    stmt = select(Runbook).where(Runbook.id == runbook_id, Runbook.tenant_id == tenant_id)
    if project_id:
        stmt = stmt.where(Runbook.project_id == project_id)
    original = db.scalars(stmt).first()
    if not original:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="runbook not found")
    
    new_runbook = Runbook(
        name=f"{original.name} (Copy)",
        yaml=original.yaml,
        tenant_id=tenant_id,
        project_id=project_id,
    )
    db.add(new_runbook)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="duplicate runbook name already exists",
        )
    db.refresh(new_runbook)
    
    write_audit(
        actor_type="user",
        actor_id=getattr(request.state, "user_email", "unknown"),
        tenant_id=tenant_id,
        action="runbook.duplicate",
        resource_type="runbook",
        resource_id=new_runbook.id,
        payload={"original_id": runbook_id, "name": new_runbook.name},
    )
    
    return RunbookRead.model_validate(new_runbook)


@router.post("/runbooks/{runbook_id}/archive", response_model=RunbookRead)
def archive_runbook(
    runbook_id: str,
    request: Request,
    db: Session = Depends(get_db),
    _auth: None = Depends(authorize("write", "runbook")),
) -> RunbookRead:
    """Archive a runbook (soft delete - mark as archived)."""
    tenant_id, project_id = get_tenant_and_project(request, db)
    stmt = select(Runbook).where(Runbook.id == runbook_id, Runbook.tenant_id == tenant_id)
    if project_id:
        stmt = stmt.where(Runbook.project_id == project_id)
    runbook = db.scalars(stmt).first()
    if not runbook:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="runbook not found")
    
    # TODO: Add archived flag to model
    write_audit(
        actor_type="user",
        actor_id=getattr(request.state, "user_email", "unknown"),
        tenant_id=tenant_id,
        action="runbook.archive",
        resource_type="runbook",
        resource_id=runbook_id,
        payload={"name": runbook.name},
    )
    
    return RunbookRead.model_validate(runbook)

