from __future__ import annotations

import json
import time
from typing import Any

from .schemas import PLANNER_OUT, REVIEWER_OUT, TOOLCALLER_OUT


def stub_planner(runbook_yaml: str, context: dict[str, Any]) -> dict[str, Any]:
    """Deterministic planner stub."""
    try:
        import yaml
    except ImportError:
        # Fallback if yaml not available
        return {"steps": []}

    data = yaml.safe_load(runbook_yaml) or {}
    steps = data.get("steps", [])
    planned = []
    for step in steps:
        if isinstance(step, dict):
            planned.append(
                {
                    "name": step.get("name", ""),
                    "tool": step.get("tool", ""),
                    "args": step.get("input", {}),
                }
            )
    return {"steps": planned}


def stub_toolcaller(step_name: str, tool: str, context: dict[str, Any]) -> dict[str, Any]:
    """Deterministic toolcaller stub."""
    return {
        "tool": tool,
        "args": context.get("default_args", {}),
        "confidence": 0.9,
        "rationale": f"Stub: using {tool} for {step_name}",
    }


def stub_reviewer(tool: str, args: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    """Deterministic reviewer stub."""
    allowlist = policy.get("tool_allowlist", {})
    allowed = False
    for role_tools in allowlist.values():
        if tool in role_tools:
            allowed = True
            break
    if allowed:
        return {"decision": "allow", "reasons": ["tool in allowlist"]}
    return {"decision": "block", "reasons": ["tool not in allowlist"]}


async def llm_stub(role: str, system: str, user: str) -> dict[str, Any]:
    """Stub LLM that returns deterministic JSON with minimal tokens/cost."""
    time.sleep(0.05)  # 50ms latency
    if role == "planner":
        result = stub_planner(user, {})
    elif role == "toolcaller":
        parts = user.split("|")
        result = stub_toolcaller(parts[0] if parts else "", parts[1] if len(parts) > 1 else "", {})
    elif role == "reviewer":
        import json as json_lib

        parts = user.split("|")
        tool = parts[0] if parts else ""
        args_str = parts[1] if len(parts) > 1 else "{}"
        policy_str = parts[2] if len(parts) > 2 else "{}"
        args = json_lib.loads(args_str)
        policy = json_lib.loads(policy_str)
        result = stub_reviewer(tool, args, policy)
    else:
        result = {}
    return {
        "text": json.dumps(result),
        "tokens_in": 10,
        "tokens_out": 20,
        "latency_ms": 50,
        "cost_usd": 0.0,
    }

