from __future__ import annotations

import time
from typing import Any, Callable, Dict, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from opentelemetry import trace
from prometheus_client import Counter, Histogram
from sqlalchemy import select
from sqlalchemy.orm import Session

from adapters.github import adapter as github_real
from adapters.github import mock as github_mock
from adapters.jira import adapter as jira_real
from adapters.jira import mock as jira_mock
from adapters.k8s import adapter as k8s_real
from adapters.k8s import mock as k8s_mock
from adapters.pagerduty import adapter as pagerduty_real
from adapters.pagerduty import mock as pagerduty_mock
from app.audit import write_audit
from app.feature_flags import which_adapter
from app.policy_guard import guard_tool_call, parse_policy
from app.db import get_db
from app.models import Policy
from app.schemas import PolicyRead
from app.billing.quotas import check_quota, enforce_quota, QuotaExceeded
from app.tenancy import get_tenant_and_project
from adapters.types import AdapterResponse, ToolCall
from pydantic import BaseModel, Field

router = APIRouter()
tracer = trace.get_tracer(__name__)

adapter_invocations_total = Counter(
    "adapter_invocations_total",
    "Adapter invocation counts",
    ["adapter", "tool", "dry_run"],
)
adapter_latency_seconds = Histogram(
    "adapter_latency_seconds",
    "Adapter latency seconds",
    ["adapter", "tool"],
)

ADAPTERS: dict[str, dict[str, Any]] = {
    "github": {"real": github_real, "mock": github_mock},
    "jira": {"real": jira_real, "mock": jira_mock},
    "k8s": {"real": k8s_real, "mock": k8s_mock},
    "pagerduty": {"real": pagerduty_real, "mock": pagerduty_mock},
}


def pick_adapter(tool_name: str, use_real: bool = False) -> Any | None:
    namespace = tool_name.split(".")[0]
    entry = ADAPTERS.get(namespace, {})
    if use_real and "real" in entry:
        return entry["real"]
    return entry.get("mock")


def get_user_roles(
    request: Request,
    x_roles: Optional[str] = Header(default=None),
) -> list[str]:
    # Get roles from request state (set by middleware from JWT or session)
    if hasattr(request.state, "user_roles") and request.state.user_roles:
        return request.state.user_roles

    # Fallback to header
    if x_roles:
        return [role.strip() for role in x_roles.split(",") if role.strip()]

    # Default
    return ["Admin"]


def _latest_policy(db: Session, name: str = "default") -> PolicyRead | None:
    stmt = select(Policy).where(Policy.name == name).order_by(Policy.created_at.desc())
    obj = db.scalars(stmt).first()
    if obj:
        return PolicyRead.model_validate(obj)
    return None


class ToolRequest(BaseModel):
    tool: str = Field(..., examples=["github.rollback_release"])
    args: Dict[str, Any] = Field(default_factory=dict)
    dryRun: bool = True
    idempotencyKey: Optional[str] = None


class ToolPlanResponse(BaseModel):
    willCall: bool = True
    tool: str
    dryRun: bool
    args: Dict[str, Any]
    adapterMode: str | None = None  # "real" or "mock"


@router.post("/tools/plan", response_model=ToolPlanResponse)
async def plan_tool(
    req: ToolRequest,
    request: Request,
    db: Session = Depends(get_db),
    user_roles: list[str] = Depends(get_user_roles),
) -> ToolPlanResponse:
    policy = _latest_policy(db)
    parsed_policy = parse_policy(policy.yaml) if policy else {}
    guard_tool_call(req.tool, req.args, user_roles, parsed_policy)

    # Check which adapter would be used (for info, doesn't affect plan)
    request_headers = {}
    adapter_mode = which_adapter(req.tool, request_headers)

    return ToolPlanResponse(
        willCall=True, tool=req.tool, dryRun=req.dryRun, args=req.args, adapterMode=adapter_mode
    )


@router.post("/tools/invoke")
async def invoke_tool(
    req: ToolRequest,
    request: Request,
    db: Session = Depends(get_db),
    user_roles: list[str] = Depends(get_user_roles),
    x_adapter_real: Optional[str] = Header(default=None),
) -> AdapterResponse:
    policy = _latest_policy(db)
    parsed_policy = parse_policy(policy.yaml) if policy else {}
    guard_tool_call(req.tool, req.args, user_roles, parsed_policy)

    # Check quotas
    tenant_id, _ = get_tenant_and_project(request, db)
    response_headers = {}
    try:
        # Projected usage: 1 adapter call
        projected = {"adapter_calls": 1, "tokens": 0, "cost": 0.01}  # Estimate
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

    # Check for warnings
    is_warning, quota_info = check_quota(db, tenant_id)
    if is_warning:
        response_headers["X-Quota-Warn"] = "true"

    use_real = x_adapter_real in ("github", "k8s", "jira", "pagerduty")
    adapter_mod = pick_adapter(req.tool, use_real=use_real)
    if adapter_mod is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"no adapter registered for {req.tool}"
        )

    call: ToolCall = {
        "name": req.tool,
        "input": req.args,
        "dryRun": req.dryRun,
        "idempotencyKey": req.idempotencyKey,
    }
    adapter_name = adapter_mod.__name__.split(".")[-1]
    adapter_invocations_total.labels(adapter=adapter_name, tool=req.tool, dry_run=str(req.dryRun)).inc()

    start = time.perf_counter()
    with tracer.start_as_current_span("tools.invoke") as span:
        span.set_attribute("tool.name", req.tool)
        span.set_attribute("tool.dry_run", req.dryRun)
        result = await adapter_mod.invoke(call)
    adapter_latency_seconds.labels(adapter=adapter_name, tool=req.tool).observe(time.perf_counter() - start)
    
    # Audit log
    tenant_id_for_audit = tenant_id if tenant_id else None
    write_audit(
        actor_type="user",
        actor_id=request.state.user_email if hasattr(request.state, "user_email") else "unknown",
        tenant_id=tenant_id_for_audit,
        action="tools.invoke",
        resource_type="tool",
        resource_id=req.tool,
        payload={"args": req.args, "dry_run": req.dryRun, "adapter": adapter_name},
    )
    
    # Return response with quota warning headers if needed
    if response_headers:
        from fastapi import Response as FastAPIResponse
        import json
        return FastAPIResponse(
            content=json.dumps(result.model_dump() if hasattr(result, "model_dump") else result.dict()),
            media_type="application/json",
            headers=response_headers,
        )
    return result

