from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Iterable

import yaml
from fastapi import HTTPException, status
from jsonschema import Draft202012Validator
from prometheus_client import Counter

TOOL_SCHEMA_DIR = Path(__file__).parent / "tool_schemas"

policy_blocks_total = Counter("policy_blocks_total", "Policy blocks by reason", ["reason"])


def _load_schema(tool: str) -> dict[str, Any] | None:
    schema_path = TOOL_SCHEMA_DIR / f"{tool}.schema.json"
    if schema_path.exists():
        with schema_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    return None


def parse_policy(yaml_str: str) -> dict[str, Any]:
    data = yaml.safe_load(yaml_str) or {}
    if not isinstance(data, dict):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="policy yaml invalid")
    return data


def check_allowlist(user_roles: Iterable[str], tool: str, policy: dict[str, Any]) -> list[str]:
    allowlist = policy.get("tool_allowlist") or {}
    for role in user_roles:
        tools = allowlist.get(role, [])
        if tool in tools:
            return []
    if allowlist:
        return [tool]
    return []


def check_budgets(run_cost_tokens: int, run_cost_usd: float, policy: dict[str, Any]) -> bool:
    budgets = policy.get("budgets") or {}
    max_tokens = budgets.get("max_tokens_per_run")
    max_usd = budgets.get("max_cost_per_run_usd")
    if max_tokens is not None and run_cost_tokens > max_tokens:
        return False
    if max_usd is not None and run_cost_usd > max_usd:
        return False
    return True


def validate_tool_input(tool: str, payload: dict[str, Any]) -> list[str]:
    schema = _load_schema(tool)
    if not schema:
        return []
    validator = Draft202012Validator(schema)
    errors = []
    for err in validator.iter_errors(payload):
        errors.append(err.message)
    return errors


def _check_k8s_namespace(tool: str, payload: dict[str, Any]) -> None:
    """Check namespace allowlist for k8s tools."""
    if not tool.startswith("k8s."):
        return
    
    namespace = payload.get("namespace")
    if not namespace:
        return  # Some k8s tools don't require namespace
    
    allowlist_str = os.getenv("K8S_NAMESPACE_ALLOWLIST", "[]")
    try:
        allowlist = json.loads(allowlist_str)
    except Exception:
        allowlist = []
    
    if allowlist and namespace not in allowlist:
        policy_blocks_total.labels(reason="k8s_namespace").inc()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"namespace '{namespace}' not in allowlist: {allowlist}",
        )


def guard_tool_call(tool: str, payload: dict[str, Any], user_roles: list[str], policy: dict[str, Any]) -> None:
    violations = check_allowlist(user_roles, tool, policy)
    if violations:
        policy_blocks_total.labels(reason="allowlist").inc()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"tool not allowed for roles {user_roles}",
        )

    schema_errors = validate_tool_input(tool, payload)
    if schema_errors:
        policy_blocks_total.labels(reason="schema").inc()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"errors": schema_errors},
        )

    # K8s-specific checks
    _check_k8s_namespace(tool, payload)

    if not check_budgets(0, 0.0, policy):
        policy_blocks_total.labels(reason="budget").inc()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="budget exceeded",
        )


