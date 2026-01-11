from __future__ import annotations

from datetime import datetime
from typing import Any

from temporalio import workflow

from . import activities
from .utils import make_idempotency_key


@workflow.defn
class RunbookWorkflow:
    @workflow.run
    async def run(self, run_id: str, mode: str = "execute") -> dict[str, Any]:
        ctx = await workflow.execute_activity(
            activities.load_context,
            run_id,
            schedule_to_close_timeout=60,
        )
        dry_run = mode != "execute"
        steps = ctx.get("runbook", {}).get("steps", [])
        policy = ctx.get("policy", {})
        context = ctx.get("context", {})
        
        # Initialize budget tracking
        totals = {
            "tokens_in": 0,
            "tokens_out": 0,
            "latency_ms": 0,
            "cost_usd": 0.0,
        }
        budgets = policy.get("budgets", {})
        max_tokens = budgets.get("max_tokens_per_run")
        max_cost = budgets.get("max_cost_per_run_usd")
        
        for step in steps:
            name = step.get("name", "")
            tool = step.get("tool", "")
            await workflow.execute_activity(
                activities.record_step,
                run_id,
                name,
                {"status": "pending", "tool": tool, "input": step.get("input")},
                schedule_to_close_timeout=30,
            )

            # Check budget before proceeding
            if max_tokens is not None and totals["tokens_in"] + totals["tokens_out"] >= max_tokens:
                await workflow.execute_activity(
                    activities.record_step,
                    run_id,
                    name,
                    {"status": "skipped", "error": {"budget": "max_tokens_per_run exceeded"}},
                    schedule_to_close_timeout=30,
                )
                continue
            if max_cost is not None and totals["cost_usd"] >= max_cost:
                await workflow.execute_activity(
                    activities.record_step,
                    run_id,
                    name,
                    {"status": "skipped", "error": {"budget": "max_cost_per_run_usd exceeded"}},
                    schedule_to_close_timeout=30,
                )
                continue
            
            val = await workflow.execute_activity(
                activities.policy_validate,
                step,
                policy,
                ctx.get("user_roles", []),
                context,
                schedule_to_close_timeout=30,
            )
            if not val["ok"]:
                await workflow.execute_activity(
                    activities.record_step,
                    run_id,
                    name,
                    {"status": "skipped", "error": {"policy": val["reasons"]}},
                    schedule_to_close_timeout=30,
                )
                continue
            
            # Check if precondition requires approval
            if val.get("require_approval"):
                if name not in ctx.get("needs_approval", {}):
                    # Create approval if not exists
                    pass  # Approvals should be created at run creation time

            if step.get("requires_approval") or name in ctx.get("needs_approval", {}):
                approval_id = ctx.get("needs_approval", {}).get(name, {}).get("id")
                approved = await workflow.execute_activity(
                    activities.wait_for_approval,
                    approval_id,
                    schedule_to_close_timeout=4000,
                )
                if not approved:
                    await workflow.execute_activity(
                        activities.record_step,
                        run_id,
                        name,
                        {"status": "skipped", "error": {"approval": "timeout"}},
                        schedule_to_close_timeout=30,
                    )
                    continue

            plan = await workflow.execute_activity(
                activities.plan_step,
                step,
                ctx,
                schedule_to_close_timeout=120,  # Longer timeout for LLM calls
            )
            
            # Check if brain blocked this step
            if plan.get("decision") == "block":
                await workflow.execute_activity(
                    activities.record_step,
                    run_id,
                    name,
                    {"status": "skipped", "error": {"brain": plan.get("reasons", [])}},
                    schedule_to_close_timeout=30,
                )
                continue
            
            await workflow.execute_activity(
                activities.record_step,
                run_id,
                name,
                {"status": "running", "started_at": datetime.utcnow(), "idempotency_key": plan["idempotencyKey"]},
                schedule_to_close_timeout=30,
            )

            try:
                res = await workflow.execute_activity(
                    activities.invoke_adapter,
                    plan["tool"],
                    plan["args"],
                    dry_run,
                    plan["idempotencyKey"],
                    schedule_to_close_timeout=60,
                    retry_policy=workflow.RetryPolicy(
                        initial_interval=1.0, backoff_coefficient=2.0, maximum_attempts=4, maximum_interval=30.0
                    ),
                )
                # Merge brain usage into output if present
                output = res.copy()
                step_usage = plan.get("usage", {})
                if step_usage:
                    output["usage"] = step_usage
                    # Update totals
                    totals["tokens_in"] += step_usage.get("tokens_in", 0)
                    totals["tokens_out"] += step_usage.get("tokens_out", 0)
                    totals["latency_ms"] += step_usage.get("latency_ms", 0)
                    totals["cost_usd"] += step_usage.get("cost_usd", 0.0)
                
                # Update run metrics with totals
                await workflow.execute_activity(
                    activities.update_run_totals,
                    run_id,
                    totals,
                    schedule_to_close_timeout=30,
                )
                
                await workflow.execute_activity(
                    activities.record_step,
                    run_id,
                    name,
                    {"status": "succeeded", "output": output, "ended_at": datetime.utcnow()},
                    schedule_to_close_timeout=30,
                )
            except Exception as exc:
                await workflow.execute_activity(
                    activities.record_step,
                    run_id,
                    name,
                    {"status": "failed", "error": {"msg": str(exc)}, "ended_at": datetime.utcnow()},
                    schedule_to_close_timeout=30,
                )
                if comp := step.get("compensate"):
                    try:
                        cres = await workflow.execute_activity(
                            activities.compensate,
                            comp.get("tool", ""),
                            comp.get("input", {}),
                            dry_run,
                            plan["idempotencyKey"],
                            schedule_to_close_timeout=60,
                        )
                        await workflow.execute_activity(
                            activities.record_step,
                            run_id,
                            name,
                            {
                                "status": "compensated",
                                "output": {"compensation": cres},
                                "ended_at": datetime.utcnow(),
                            },
                            schedule_to_close_timeout=30,
                        )
                    except Exception as comp_exc:
                        await workflow.execute_activity(
                            activities.record_step,
                            run_id,
                            name,
                            {
                                "error": {"compensation_failed": str(comp_exc)},
                                "ended_at": datetime.utcnow(),
                            },
                            schedule_to_close_timeout=30,
                        )
                raise

        if mode == "shadow":
            await workflow.execute_activity(
                activities.compute_shadow,
                run_id,
                ctx,
                schedule_to_close_timeout=30,
            )

        return {"ok": True, "mode": mode}

