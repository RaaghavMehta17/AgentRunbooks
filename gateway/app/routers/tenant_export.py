"""Tenant export/import endpoints for DR and migration."""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..db import get_db
from ..models import (
    Approval,
    IncidentLink,
    Policy,
    Project,
    RoleBinding,
    Run,
    Runbook,
    Step,
    Tenant,
)
from ..rbac import authorize
from ..tenancy import get_tenant_and_project

router = APIRouter(prefix="/export", tags=["export"])


@router.get("/tenant/{tenant_id}")
async def export_tenant(
    tenant_id: str,
    request: Request,
    db: Session = Depends(get_db),
    _auth: None = Depends(authorize("read", "*")),
) -> Response:
    """Export tenant data as JSON bundle for DR/migration."""
    # Verify tenant exists and user has access
    tenant = db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Build export bundle
    bundle: Dict[str, Any] = {
        "version": "1.0",
        "tenant_id": tenant_id,
        "tenant_name": tenant.name,
        "exported_at": None,
        "summary": {},
        "data": {},
    }

    # Export projects
    projects = db.execute(select(Project).where(Project.tenant_id == tenant_id)).scalars().all()
    bundle["data"]["projects"] = [
        {
            "id": p.id,
            "name": p.name,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in projects
    ]
    bundle["summary"]["projects"] = len(projects)

    # Export runbooks
    runbooks = db.execute(select(Runbook).where(Runbook.tenant_id == tenant_id)).scalars().all()
    bundle["data"]["runbooks"] = [
        {
            "id": r.id,
            "name": r.name,
            "yaml": r.yaml,
            "project_id": r.project_id,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in runbooks
    ]
    bundle["summary"]["runbooks"] = len(runbooks)

    # Export policies
    policies = db.execute(select(Policy).where(Policy.tenant_id == tenant_id)).scalars().all()
    bundle["data"]["policies"] = [
        {
            "id": p.id,
            "name": p.name,
            "yaml": p.yaml,
            "version": p.version,
            "project_id": p.project_id,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in policies
    ]
    bundle["summary"]["policies"] = len(policies)

    # Export runs metadata
    runs = db.execute(select(Run).where(Run.tenant_id == tenant_id)).scalars().all()
    bundle["data"]["runs"] = [
        {
            "id": r.id,
            "runbook_id": r.runbook_id,
            "status": r.status,
            "metrics": r.metrics,
            "project_id": r.project_id,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in runs
    ]
    bundle["summary"]["runs"] = len(runs)

    # Export steps
    run_ids = [r.id for r in runs]
    steps = []
    if run_ids:
        steps_query = select(Step).where(Step.run_id.in_(run_ids))
        steps = db.execute(steps_query).scalars().all()
    bundle["data"]["steps"] = [
        {
            "id": s.id,
            "run_id": s.run_id,
            "name": s.name,
            "tool": s.tool,
            "status": s.status,
            "input": s.input,
            "output": s.output,
            "error": s.error,
            "created_at": s.started_at.isoformat() if s.started_at else None,
        }
        for s in steps
    ]
    bundle["summary"]["steps"] = len(steps)

    # Export approvals
    approvals = []
    if run_ids:
        approvals_query = select(Approval).where(Approval.run_id.in_(run_ids))
        approvals = db.execute(approvals_query).scalars().all()
    bundle["data"]["approvals"] = [
        {
            "id": a.id,
            "run_id": a.run_id,
            "step_name": a.step_name,
            "status": a.status,
            "approved_by": a.approved_by,
            "approved_at": a.approved_at.isoformat() if a.approved_at else None,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in approvals
    ]
    bundle["summary"]["approvals"] = len(approvals)

    # Export incident links
    incident_links = []
    if run_ids:
        links_query = select(IncidentLink).where(IncidentLink.run_id.in_(run_ids))
        incident_links = db.execute(links_query).scalars().all()
    bundle["data"]["incident_links"] = [
        {
            "id": il.id,
            "run_id": il.run_id,
            "pd_incident_id": il.pd_incident_id,
            "jira_issue_key": il.jira_issue_key,
            "created_at": il.created_at.isoformat() if il.created_at else None,
        }
        for il in incident_links
    ]
    bundle["summary"]["incident_links"] = len(incident_links)

    # Export role bindings
    role_bindings = db.execute(select(RoleBinding).where(RoleBinding.tenant_id == tenant_id)).scalars().all()
    bundle["data"]["role_bindings"] = [
        {
            "id": rb.id,
            "tenant_id": rb.tenant_id,
            "project_id": rb.project_id,
            "subject_type": rb.subject_type,
            "subject_id": rb.subject_id,
            "role": rb.role,
            "created_at": rb.created_at.isoformat() if rb.created_at else None,
        }
        for rb in role_bindings
    ]
    bundle["summary"]["role_bindings"] = len(role_bindings)

    # Export audit hashes (for integrity verification)
    # TODO: Query audit logs and compute hashes
    bundle["data"]["audit_hashes"] = {
        "note": "Audit log integrity hashes would be computed here",
        "algorithm": "sha256",
    }

    from datetime import datetime

    bundle["exported_at"] = datetime.utcnow().isoformat()

    # Audit log
    write_audit(
        db=db,
        action="export.tenant",
        actor_type="user",
        actor_id=request.state.user_email if hasattr(request.state, "user_email") else "unknown",
        resource_type="tenant",
        resource_id=tenant_id,
        payload={"summary": bundle["summary"]},
    )

    # Stream JSON response (chunked for large exports)
    json_str = json.dumps(bundle, indent=2)
    return Response(
        content=json_str,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="tenant_{tenant_id}_export.json"'},
    )


@router.post("/import/tenant")
async def import_tenant(
    request: Request,
    db: Session = Depends(get_db),
    _auth: None = Depends(authorize("write", "*")),
) -> Dict[str, Any]:
    """Import tenant data from JSON bundle."""
    # Parse JSON from request body
    try:
        bundle = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")

    # Validate bundle structure
    if not isinstance(bundle, dict) or "data" not in bundle:
        raise HTTPException(status_code=400, detail="Invalid bundle format: missing 'data'")

    # Get target tenant/project from headers or create default
    tenant_id, project_id = get_tenant_and_project(request, db)

    # ID mapping for remapping imported IDs
    id_mapping: Dict[str, Dict[str, str]] = {
        "projects": {},
        "runbooks": {},
        "policies": {},
        "runs": {},
        "steps": {},
        "approvals": {},
        "incident_links": {},
    }

    summary: Dict[str, int] = {
        "projects_created": 0,
        "runbooks_created": 0,
        "policies_created": 0,
        "runs_created": 0,
        "steps_created": 0,
        "approvals_created": 0,
        "incident_links_created": 0,
        "role_bindings_created": 0,
    }

    try:
        # Import projects
        for proj_data in bundle.get("data", {}).get("projects", []):
            old_id = proj_data["id"]
            new_id = str(uuid.uuid4())
            id_mapping["projects"][old_id] = new_id

            project = Project(
                id=new_id,
                tenant_id=tenant_id,
                name=proj_data["name"],
            )
            db.add(project)
            summary["projects_created"] += 1

        db.flush()

        # Import runbooks
        for rb_data in bundle.get("data", {}).get("runbooks", []):
            old_id = rb_data["id"]
            new_id = str(uuid.uuid4())
            id_mapping["runbooks"][old_id] = new_id

            project_id_mapped = id_mapping["projects"].get(rb_data.get("project_id"), project_id)

            runbook = Runbook(
                id=new_id,
                tenant_id=tenant_id,
                project_id=project_id_mapped,
                name=rb_data["name"],
                yaml=rb_data["yaml"],
            )
            db.add(runbook)
            summary["runbooks_created"] += 1

        db.flush()

        # Import policies
        for pol_data in bundle.get("data", {}).get("policies", []):
            old_id = pol_data["id"]
            new_id = str(uuid.uuid4())
            id_mapping["policies"][old_id] = new_id

            project_id_mapped = id_mapping["projects"].get(pol_data.get("project_id"), project_id)

            policy = Policy(
                id=new_id,
                tenant_id=tenant_id,
                project_id=project_id_mapped,
                name=pol_data["name"],
                yaml=pol_data["yaml"],
                version=pol_data.get("version", "1.0"),
            )
            db.add(policy)
            summary["policies_created"] += 1

        db.flush()

        # Import runs
        for run_data in bundle.get("data", {}).get("runs", []):
            old_id = run_data["id"]
            new_id = str(uuid.uuid4())
            id_mapping["runs"][old_id] = new_id

            runbook_id_mapped = id_mapping["runbooks"].get(run_data.get("runbook_id"))
            if not runbook_id_mapped:
                continue  # Skip if runbook not imported

            project_id_mapped = id_mapping["projects"].get(run_data.get("project_id"), project_id)

            run = Run(
                id=new_id,
                tenant_id=tenant_id,
                project_id=project_id_mapped,
                runbook_id=runbook_id_mapped,
                status=run_data["status"],
                metrics=run_data.get("metrics", {}),
            )
            db.add(run)
            summary["runs_created"] += 1

        db.flush()

        # Import steps
        for step_data in bundle.get("data", {}).get("steps", []):
            run_id_mapped = id_mapping["runs"].get(step_data.get("run_id"))
            if not run_id_mapped:
                continue  # Skip if run not imported

            step = Step(
                id=str(uuid.uuid4()),
                run_id=run_id_mapped,
                name=step_data["name"],
                tool=step_data["tool"],
                status=step_data["status"],
                input=step_data.get("input"),
                output=step_data.get("output"),
                error=step_data.get("error"),
            )
            db.add(step)
            summary["steps_created"] += 1

        db.flush()

        # Import approvals
        for appr_data in bundle.get("data", {}).get("approvals", []):
            run_id_mapped = id_mapping["runs"].get(appr_data.get("run_id"))
            if not run_id_mapped:
                continue

            approval = Approval(
                id=str(uuid.uuid4()),
                run_id=run_id_mapped,
                step_name=appr_data["step_name"],
                status=appr_data["status"],
                approved_by=appr_data.get("approved_by"),
            )
            db.add(approval)
            summary["approvals_created"] += 1

        db.flush()

        # Import incident links
        for link_data in bundle.get("data", {}).get("incident_links", []):
            run_id_mapped = id_mapping["runs"].get(link_data.get("run_id"))
            if not run_id_mapped:
                continue

            incident_link = IncidentLink(
                id=str(uuid.uuid4()),
                run_id=run_id_mapped,
                pd_incident_id=link_data.get("pd_incident_id"),
                jira_issue_key=link_data.get("jira_issue_key"),
            )
            db.add(incident_link)
            summary["incident_links_created"] += 1

        db.flush()

        # Import role bindings
        for rb_data in bundle.get("data", {}).get("role_bindings", []):
            project_id_mapped = id_mapping["projects"].get(rb_data.get("project_id"), project_id)

            role_binding = RoleBinding(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                project_id=project_id_mapped if project_id_mapped else None,
                subject_type=rb_data["subject_type"],
                subject_id=rb_data["subject_id"],
                role=rb_data["role"],
            )
            db.add(role_binding)
            summary["role_bindings_created"] += 1

        db.commit()

        # Audit log
        write_audit(
            db=db,
            action="import.tenant",
            actor_type="user",
            actor_id=request.state.user_email if hasattr(request.state, "user_email") else "unknown",
            resource_type="tenant",
            resource_id=tenant_id,
            payload={"summary": summary, "source_tenant": bundle.get("tenant_id")},
        )

        return {
            "status": "success",
            "tenant_id": tenant_id,
            "summary": summary,
            "id_mapping": {k: len(v) for k, v in id_mapping.items()},
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")

