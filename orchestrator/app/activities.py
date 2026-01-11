from __future__ import annotations

import asyncio
import os
import time
from datetime import datetime
from typing import Any

import yaml
from jsonschema import Draft202012Validator
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from opentelemetry import trace
from prometheus_client import Counter, Histogram

from adapters.github import adapter as github_real
from adapters.github import mock as github_mock
from adapters.jira import mock as jira_mock
from adapters.k8s import mock as k8s_mock
from adapters.pagerduty import mock as pagerduty_mock
from app import models  # type: ignore
from .utils import make_idempotency_key, json_safe

# Cache for brain planning results per run
_brain_cache: dict[str, dict[str, Any]] = {}

tracer = trace.get_tracer(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")

engine = create_engine(DATABASE_URL, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

ADAPTERS: dict[str, dict[str, Any]] = {
    "github": {"real": github_real, "mock": github_mock},
    "jira": {"mock": jira_mock},
    "k8s": {"mock": k8s_mock},
    "pagerduty": {"mock": pagerduty_mock},
}

step_attempts_total = Counter("step_attempts_total", "Step attempts", ["tool", "status"])
step_compensations_total = Counter(
    "step_compensations_total", "Step compensations", ["tool", "status"]
)
adapter_latency_seconds = Histogram("adapter_latency_seconds", "Adapter latency seconds", ["tool"])
shadow_match_score = Histogram("shadow_match_score", "Shadow match score", [])
shadow_policy_violations_total = Counter("shadow_policy_violations_total", "Shadow policy violations", [])


def pick_adapter(tool_name: str, use_real: bool = False) -> Any | None:
    namespace = tool_name.split(".")[0]
    entry = ADAPTERS.get(namespace, {})
    if use_real and "real" in entry:
        return entry["real"]
    return entry.get("mock")


def _load_schema(tool: str) -> dict[str, Any] | None:
    from pathlib import Path

    schema_path = Path(__file__).parents[2] / "gateway" / "app" / "tool_schemas" / f"{tool}.schema.json"
    if schema_path.exists():
        import json

        with schema_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    return None


def load_context(run_id: str) -> dict[str, Any]:
    with SessionLocal() as db:
        run = db.get(models.Run, run_id)
        if not run:
            raise RuntimeError("run not found")
        runbook = db.get(models.Runbook, run.runbook_id)
        if not runbook:
            raise RuntimeError("runbook not found")
        policy = (
            db.execute(select(models.Policy).order_by(models.Policy.created_at.desc())).scalars().first()
        )
        policy_yaml = policy.yaml if policy else "{}"
        rb = yaml.safe_load(runbook.yaml) or {}
        pol = yaml.safe_load(policy_yaml) or {}
        approvals = (
            db.execute(select(models.Approval).where(models.Approval.run_id == run_id)).scalars().all()
        )
        context = run.metrics.get("context", {})
        return {
            "run": {
                "id": run.id,
                "mode": run.metrics.get("mode", "execute"),
                "expected": run.metrics.get("expected", {}),
            },
            "runbook": rb,
            "policy": pol,
            "user_roles": ["Admin"],
            "approvals": approvals,
            "needs_approval": {a.step_name: a for a in approvals},
            "context": context,
        }


def policy_validate(
    step: dict[str, Any], policy: dict[str, Any], user_roles: list[str], context: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Validate step against policy: allowlist, schema, and preconditions."""
    tool = step.get("tool", "")
    allowlist = policy.get("tool_allowlist", {})
    allowed = False
    for role in user_roles:
        tools = allowlist.get(role, [])
        if tool in tools:
            allowed = True
            break
    reasons: list[str] = []
    if allowlist and not allowed:
        reasons.append("tool not allowed for roles")
    
    # Schema validation
    schema = _load_schema(tool)
    if schema:
        validator = Draft202012Validator(schema)
        errors = [err.message for err in validator.iter_errors(step.get("input", {}))]
        if errors:
            reasons.extend(errors)
    
    # Preconditions
    preconditions = policy.get("preconditions", [])
    if preconditions and context:
        try:
            import sys
            from pathlib import Path
            
            # Add policy_engine to path
            policy_engine_path = Path(__file__).parents[1]
            if str(policy_engine_path) not in sys.path:
                sys.path.insert(0, str(policy_engine_path))
            
            from policy_engine import decide
            
            decision = decide(preconditions, step, context)
            if decision == "block":
                reasons.append("precondition blocked")
            elif decision == "require_approval":
                # Mark for approval but don't block yet
                return {"ok": True, "reasons": [], "require_approval": True}
        except Exception as e:
            # If policy_engine not available, skip preconditions
            import logging
            logging.warning(f"Precondition evaluation failed: {e}")
            pass
    
    return {"ok": not reasons, "reasons": reasons}


async def wait_for_approval(approval_id: str, timeout_s: int = 3600) -> bool:
    end_time = time.time() + timeout_s
    while time.time() < end_time:
        with SessionLocal() as db:
            approval = db.get(models.Approval, approval_id)
            if approval and approval.approved:
                return True
        await asyncio.sleep(3)
    return False


async def plan_step(step: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    """Plan step using agent brain, caching results per run."""
    run_id = ctx["run"]["id"]
    
    # Check cache or call brain
    if run_id not in _brain_cache:
        try:
            from agents.brain import plan_and_review
            import yaml
            
            runbook_yaml = yaml.dump(ctx.get("runbook", {}))
            policy_yaml = yaml.dump(ctx.get("policy", {}))
            context = ctx.get("context", {})
            
            brain_result = await plan_and_review(runbook_yaml, policy_yaml, context)
            _brain_cache[run_id] = brain_result
        except Exception as e:
            # Fallback to simple planning
            import logging
            logging.warning(f"Brain planning failed, using fallback: {e}")
            _brain_cache[run_id] = {"planned": [], "usage": {}}
    
    # Find matching planned step
    planned_steps = _brain_cache[run_id].get("planned", [])
    step_name = step.get("name", "")
    planned_step = next((p for p in planned_steps if p.get("name") == step_name), None)
    
    if planned_step:
        tool = planned_step.get("tool", step.get("tool", ""))
        args = planned_step.get("args", step.get("input", {}))
        decision = planned_step.get("decision", "allow")
        
        # If blocked, return skip signal
        if decision == "block":
            return {
                "tool": tool,
                "args": args,
                "idempotencyKey": make_idempotency_key(run_id, step_name, args),
                "decision": "block",
                "reasons": planned_step.get("reasons", []),
            }
    else:
        # Fallback
        tool = step.get("tool", "")
        args = step.get("input", {})
    
    idempotency_key = make_idempotency_key(run_id, step_name, args)
    usage = _brain_cache[run_id].get("usage", {})
    
    return {
        "tool": tool,
        "args": args,
        "idempotencyKey": idempotency_key,
        "usage": usage,  # Attach usage to step output
    }


async def invoke_adapter(tool: str, args: dict[str, Any], dry_run: bool, idempotency_key: str) -> dict[str, Any]:
    adapter_mod = pick_adapter(tool, use_real=False)
    if adapter_mod is None:
        raise RuntimeError(f"no adapter for {tool}")
    call = {"name": tool, "input": args, "dryRun": dry_run, "idempotencyKey": idempotency_key}
    with tracer.start_as_current_span("invoke_adapter") as span:
        span.set_attribute("tool", tool)
        start = time.perf_counter()
        step_attempts_total.labels(tool=tool, status="started").inc()
        result = await adapter_mod.invoke(call)
        elapsed = time.perf_counter() - start
        adapter_latency_seconds.labels(tool=tool).observe(elapsed)
        span.set_attribute("elapsed_ms", elapsed * 1000)
    if result.get("audit", {}).get("error_status", 0) in (500, 502, 503):
        # retryable
        raise RuntimeError("retryable")
    step_attempts_total.labels(tool=tool, status="finished").inc()
    return result


async def compensate(tool: str, args: dict[str, Any], dry_run: bool, idempotency_key: str) -> dict[str, Any]:
    adapter_mod = pick_adapter(tool, use_real=False)
    if adapter_mod is None:
        raise RuntimeError(f"no adapter for {tool}")
    call = {
        "name": tool,
        "input": args,
        "dryRun": dry_run,
        "idempotencyKey": f"{idempotency_key}-comp",
    }
    start = time.perf_counter()
    step_compensations_total.labels(tool=tool, status="started").inc()
    result = await adapter_mod.invoke(call)
    adapter_latency_seconds.labels(tool=tool).observe(time.perf_counter() - start)
    step_compensations_total.labels(tool=tool, status="finished").inc()
    return result


def record_step(run_id: str, step_name: str, fields: dict[str, Any]) -> None:
    with SessionLocal() as db:
        step = (
            db.query(models.Step)
            .filter(models.Step.run_id == run_id)
            .filter(models.Step.name == step_name)
            .first()
        )
        if not step:
            step = models.Step(run_id=run_id, name=step_name, tool=fields.get("tool", ""))
            db.add(step)
        for key, value in fields.items():
            if key == "status" and value is not None:
                if isinstance(value, models.StepStatus):
                    step.status = value
                else:
                    try:
                        step.status = models.StepStatus(value)
                    except Exception:
                        step.status = models.StepStatus.PENDING
            elif hasattr(step, key):
                setattr(step, key, json_safe(value))
        if fields.get("status") == models.StepStatus.RUNNING:
            step.started_at = step.started_at or datetime.utcnow()
        if fields.get("status") in {
            models.StepStatus.SUCCEEDED,
            models.StepStatus.FAILED,
            models.StepStatus.SKIPPED,
            models.StepStatus.COMPENSATED,
        }:
            step.ended_at = step.ended_at or datetime.utcnow()
        db.commit()


def update_run_totals(run_id: str, totals: dict[str, Any]) -> None:
    """Update runs.metrics with aggregated usage totals."""
    with SessionLocal() as db:
        run = db.get(models.Run, run_id)
        if not run:
            return
        metrics = run.metrics.copy() if run.metrics else {}
        metrics["tokens_in"] = totals.get("tokens_in", 0)
        metrics["tokens_out"] = totals.get("tokens_out", 0)
        metrics["latency_ms"] = totals.get("latency_ms", 0)
        metrics["cost_usd"] = totals.get("cost_usd", 0.0)
        run.metrics = metrics
        db.commit()


def compute_shadow(run_id: str, ctx: dict[str, Any]) -> None:
    """Enhanced shadow comparison with granular step diffs."""
    with SessionLocal() as db:
        run = db.get(models.Run, run_id)
        if not run:
            return
        
        # Get agent-planned steps from actual execution
        steps = db.query(models.Step).filter(models.Step.run_id == run_id).order_by(models.Step.started_at).all()
        agent_steps = [
            {"name": s.name, "tool": s.tool, "input": s.input or {}, "order_index": idx}
            for idx, s in enumerate(steps)
            if s.status in {models.StepStatus.SUCCEEDED, models.StepStatus.RUNNING, models.StepStatus.PENDING}
        ]
        
        # Get expected steps from runbook or metrics
        runbook_steps = ctx.get("runbook", {}).get("steps", [])
        expected_steps = ctx.get("run", {}).get("expected", {}).get("steps", [])
        
        # Build step comparison
        step_compare = []
        tool_matches = 0
        args_matches = 0
        order_matches = 0
        total_steps = max(len(agent_steps), len(expected_steps)) or 1
        
        # Create maps for comparison
        agent_map = {s["name"]: s for s in agent_steps}
        expected_map = {}
        for idx, exp_name in enumerate(expected_steps):
            if isinstance(exp_name, str):
                expected_map[exp_name] = {"name": exp_name, "order_index": idx}
            elif isinstance(exp_name, dict):
                expected_map[exp_name.get("name", "")] = {**exp_name, "order_index": idx}
        
        # Compare each step
        all_step_names = set(agent_map.keys()) | set(expected_map.keys())
        for step_name in all_step_names:
            agent_step = agent_map.get(step_name)
            expected_step = expected_map.get(step_name)
            
            tool_match = False
            args_field_diff = {}
            order_index_agent = agent_step.get("order_index") if agent_step else -1
            order_index_expected = expected_step.get("order_index") if expected_step else -1
            
            if agent_step and expected_step:
                # Compare tool
                agent_tool = agent_step.get("tool", "")
                expected_tool = expected_step.get("tool", "")
                tool_match = agent_tool == expected_tool
                if tool_match:
                    tool_matches += 1
                
                # Compare args (shallow diff)
                agent_input = agent_step.get("input", {})
                expected_input = expected_step.get("input", {})
                for key in set(agent_input.keys()) | set(expected_input.keys()):
                    if agent_input.get(key) != expected_input.get(key):
                        args_field_diff[key] = {
                            "agent": agent_input.get(key),
                            "expected": expected_input.get(key),
                        }
                
                if not args_field_diff:
                    args_matches += 1
                
                # Check order
                if order_index_agent == order_index_expected:
                    order_matches += 1
            
            step_compare.append({
                "name": step_name,
                "tool_match": tool_match,
                "args_field_diff": args_field_diff,
                "order_index_agent": order_index_agent,
                "order_index_expected": order_index_expected,
            })
        
        # Weighted match score: 0.5 tool, 0.3 args, 0.2 order
        tool_score = tool_matches / total_steps if total_steps > 0 else 0.0
        args_score = args_matches / total_steps if total_steps > 0 else 0.0
        order_score = order_matches / total_steps if total_steps > 0 else 0.0
        match_score = 0.5 * tool_score + 0.3 * args_score + 0.2 * order_score
        
        # Count policy violations from validation results
        policy_violations = 0
        for step in steps:
            if step.status == models.StepStatus.SKIPPED:
                error = step.error or {}
                if "policy" in error or "budget" in error:
                    policy_violations += 1
        
        # Emit metrics
        shadow_match_score.observe(match_score)
        shadow_policy_violations_total.inc(policy_violations)
        
        # Update run metrics
        metrics = run.metrics or {}
        metrics["shadow"] = {
            "enabled": True,
            "step_compare": step_compare,
            "match_score": match_score,
            "policy_violations": policy_violations,
        }
        run.metrics = metrics
        db.commit()

