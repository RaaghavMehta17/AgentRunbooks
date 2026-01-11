from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..db import get_db
from ..models import Project, RoleBinding, Tenant
from ..rbac import authorize
from ..tenancy import get_tenant_and_project

router = APIRouter()


class ProjectCreate(BaseModel):
    name: str


class ProjectRead(BaseModel):
    id: str
    tenant_id: str
    name: str
    created_at: datetime

    class Config:
        from_attributes = True


class ProjectList(BaseModel):
    projects: list[ProjectRead]


class RoleBindingCreate(BaseModel):
    subject_type: str  # 'user', 'group', 'apikey'
    subject_id: str
    role: str
    project: str | None = None  # Project name (optional)


class RoleBindingRead(BaseModel):
    id: str
    tenant_id: str
    project_id: str | None
    subject_type: str
    subject_id: str
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


class RoleBindingList(BaseModel):
    bindings: list[RoleBindingRead]


@router.post("/projects", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    request: Request,
    db: Session = Depends(get_db),
    _auth: None = Depends(authorize("write", "project")),
) -> ProjectRead:
    """Create a project (Admin only)."""
    tenant_id, _ = get_tenant_and_project(request, db)

    project = Project(tenant_id=tenant_id, name=payload.name)
    db.add(project)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"project '{payload.name}' already exists in tenant",
        )
    db.refresh(project)

    write_audit(
        actor_type="user",
        actor_id=getattr(request.state, "user_email", "unknown"),
        tenant_id=tenant_id,
        action="project.create",
        resource_type="project",
        resource_id=project.id,
        payload={"name": payload.name},
    )

    return ProjectRead.model_validate(project)


@router.get("/projects", response_model=ProjectList)
def list_projects(
    request: Request,
    db: Session = Depends(get_db),
    _auth: None = Depends(authorize("read", "project")),
) -> ProjectList:
    """List projects in tenant."""
    tenant_id, _ = get_tenant_and_project(request, db)

    stmt = select(Project).where(Project.tenant_id == tenant_id).order_by(Project.created_at.desc())
    projects = db.scalars(stmt).all()

    return ProjectList(projects=[ProjectRead.model_validate(p) for p in projects])


@router.post("/role-bindings", response_model=RoleBindingRead, status_code=status.HTTP_201_CREATED)
def create_role_binding(
    payload: RoleBindingCreate,
    request: Request,
    db: Session = Depends(get_db),
    _auth: None = Depends(authorize("write", "role_binding")),
) -> RoleBindingRead:
    """Create a role binding (Admin only)."""
    if payload.subject_type not in ("user", "group", "apikey"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="subject_type must be 'user', 'group', or 'apikey'",
        )

    tenant_id, _ = get_tenant_and_project(request, db)
    project_id = None

    if payload.project:
        project = db.scalar(
            select(Project).where(Project.tenant_id == tenant_id, Project.name == payload.project)
        )
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"project '{payload.project}' not found"
            )
        project_id = project.id

    binding = RoleBinding(
        tenant_id=tenant_id,
        project_id=project_id,
        subject_type=payload.subject_type,
        subject_id=payload.subject_id,
        role=payload.role,
    )
    db.add(binding)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="role binding already exists",
        )
    db.refresh(binding)

    write_audit(
        actor_type="user",
        actor_id=getattr(request.state, "user_email", "unknown"),
        tenant_id=tenant_id,
        action="role_binding.create",
        resource_type="role_binding",
        resource_id=binding.id,
        payload={
            "subject_type": payload.subject_type,
            "subject_id": payload.subject_id,
            "role": payload.role,
            "project_id": project_id,
        },
    )

    return RoleBindingRead.model_validate(binding)


@router.get("/role-bindings", response_model=RoleBindingList)
def list_role_bindings(
    request: Request,
    db: Session = Depends(get_db),
    _auth: None = Depends(authorize("read", "role_binding")),
) -> RoleBindingList:
    """List role bindings (Admin only)."""
    tenant_id, project_id = get_tenant_and_project(request, db)

    stmt = select(RoleBinding).where(RoleBinding.tenant_id == tenant_id)
    if project_id:
        stmt = stmt.where(
            (RoleBinding.project_id == project_id) | (RoleBinding.project_id.is_(None))
        )
    stmt = stmt.order_by(RoleBinding.created_at.desc())

    bindings = db.scalars(stmt).all()

    return RoleBindingList(bindings=[RoleBindingRead.model_validate(b) for b in bindings])

