from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import HTTPException, status
from jsonschema import Draft202012Validator

from .provider import llm_complete
from .schemas import PLANNER_OUT, REVIEWER_OUT, TOOLCALLER_OUT


def _load_prompt(role: str) -> str:
    """Load prompt template from prompts/ directory."""
    prompt_path = Path(__file__).parent / "prompts" / f"{role}.md"
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8")
    return f"You are a {role}. Follow instructions carefully."


def _validate_json(text: str, schema: dict[str, Any], role: str) -> dict[str, Any]:
    """Parse and validate JSON against schema."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{role} returned invalid JSON: {e}",
        )
    validator = Draft202012Validator(schema)
    errors = list(validator.iter_errors(data))
    if errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{role} output violates schema: {[e.message for e in errors]}",
        )
    return data


async def plan_and_review(
    runbook_yaml: str, policy_yaml: str, context: dict[str, Any]
) -> dict[str, Any]:
    """
    Orchestrate planner → toolcaller → reviewer for each step.
    Returns planned steps with decisions and aggregated usage.
    """
    try:
        import yaml
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="yaml module not available",
        )

    policy = yaml.safe_load(policy_yaml) or {}
    runbook = yaml.safe_load(runbook_yaml) or {}
    steps = runbook.get("steps", [])

    total_usage = {"tokens_in": 0, "tokens_out": 0, "latency_ms": 0, "cost_usd": 0.0}
    planned_steps = []

    # Planner: generate plan
    planner_system = _load_prompt("planner")
    planner_user = f"Runbook:\n{runbook_yaml}\n\nContext:\n{json.dumps(context, indent=2)}"
    planner_result = await llm_complete("planner", planner_system, planner_user)
    total_usage["tokens_in"] += planner_result["tokens_in"]
    total_usage["tokens_out"] += planner_result["tokens_out"]
    total_usage["latency_ms"] += planner_result["latency_ms"]
    total_usage["cost_usd"] += planner_result["cost_usd"]

    planner_out = _validate_json(planner_result["text"], PLANNER_OUT, "planner")
    planned = planner_out.get("steps", [])

    # For each step: toolcaller → reviewer
    for step in steps:
        step_name = step.get("name", "")
        step_tool = step.get("tool", "")

        # Find matching planned step
        planned_step = next((p for p in planned if p.get("name") == step_name), None)
        if not planned_step:
            planned_step = {"name": step_name, "tool": step_tool, "args": step.get("input", {})}

        # Toolcaller
        toolcaller_system = _load_prompt("toolcaller")
        toolcaller_user = f"{step_name}|{step_tool}|{json.dumps(context)}"
        toolcaller_result = await llm_complete("toolcaller", toolcaller_system, toolcaller_user)
        total_usage["tokens_in"] += toolcaller_result["tokens_in"]
        total_usage["tokens_out"] += toolcaller_result["tokens_out"]
        total_usage["latency_ms"] += toolcaller_result["latency_ms"]
        total_usage["cost_usd"] += toolcaller_result["cost_usd"]

        toolcaller_out = _validate_json(toolcaller_result["text"], TOOLCALLER_OUT, "toolcaller")
        final_tool = toolcaller_out.get("tool", step_tool)
        final_args = toolcaller_out.get("args", planned_step.get("args", {}))

        # Reviewer
        reviewer_system = _load_prompt("reviewer")
        reviewer_user = f"{final_tool}|{json.dumps(final_args)}|{json.dumps(policy)}"
        reviewer_result = await llm_complete("reviewer", reviewer_system, reviewer_user)
        total_usage["tokens_in"] += reviewer_result["tokens_in"]
        total_usage["tokens_out"] += reviewer_result["tokens_out"]
        total_usage["latency_ms"] += reviewer_result["latency_ms"]
        total_usage["cost_usd"] += reviewer_result["cost_usd"]

        reviewer_out = _validate_json(reviewer_result["text"], REVIEWER_OUT, "reviewer")

        planned_steps.append(
            {
                "name": step_name,
                "tool": final_tool,
                "args": final_args,
                "decision": reviewer_out.get("decision", "allow"),
                "reasons": reviewer_out.get("reasons", []),
            }
        )

    return {"planned": planned_steps, "usage": total_usage}

