"""Usage metering and aggregation."""

import os
from datetime import datetime, timedelta, date
from typing import Dict, Any, Optional
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from ..models import BillingUsage, Run, Step


def record_usage(
    db: Session,
    tenant_id: str,
    tokens_in: int = 0,
    tokens_out: int = 0,
    steps: int = 0,
    adapter_calls: Dict[str, int] = None,
    llm_cost: float = 0.0,
) -> None:
    """Record usage incrementally (in-memory counters, flushed periodically)."""
    # TODO: Use Redis for atomic increments
    pass


def aggregate_daily_usage(db: Session, target_date: Optional[date] = None) -> None:
    """Aggregate usage for a given day (or yesterday if not specified)."""
    if target_date is None:
        target_date = (datetime.utcnow() - timedelta(days=1)).date()

    # Get all tenants
    from ..models import Tenant
    tenants = db.execute(select(Tenant)).scalars().all()

    for tenant in tenants:
        # Calculate day start/end
        day_start = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=None)
        day_end = day_start + timedelta(days=1)

        # Aggregate runs and steps for this tenant on this day
        runs_query = select(Run).where(
            Run.tenant_id == tenant.id,
            Run.created_at >= day_start,
            Run.created_at < day_end,
        )
        runs = db.execute(runs_query).scalars().all()

        total_tokens_in = 0
        total_tokens_out = 0
        total_steps = 0
        adapter_calls: Dict[str, int] = {}
        total_llm_cost = 0.0

        for run in runs:
            # Extract metrics from run
            metrics = run.metrics or {}
            total_tokens_in += metrics.get("tokens_in", 0)
            total_tokens_out += metrics.get("tokens_out", 0)
            total_llm_cost += metrics.get("cost_usd", 0.0)

            # Count steps
            steps_query = select(Step).where(Step.run_id == run.id)
            steps = db.execute(steps_query).scalars().all()
            total_steps += len(steps)

            # Count adapter calls by type
            for step in steps:
                tool = step.tool or ""
                adapter_type = tool.split(".")[0] if "." in tool else "unknown"
                adapter_calls[adapter_type] = adapter_calls.get(adapter_type, 0) + 1

        # Calculate total cost (LLM + adapter costs)
        # Simple rate: $0.01 per adapter call (example)
        adapter_cost = sum(adapter_calls.values()) * 0.01
        total_cost = total_llm_cost + adapter_cost

        # Check if record exists
        day_datetime = datetime.combine(target_date, datetime.min.time())
        existing = db.execute(
            select(BillingUsage).where(
                BillingUsage.tenant_id == tenant.id,
                func.date(BillingUsage.day) == target_date,
            )
        ).scalar_one_or_none()

        metrics = {
            "tokens_in": total_tokens_in,
            "tokens_out": total_tokens_out,
            "steps": total_steps,
            "adapter_calls": adapter_calls,
            "llm_cost": total_llm_cost,
            "total_cost": total_cost,
        }

        if existing:
            existing.metrics = metrics
        else:
            usage = BillingUsage(
                tenant_id=tenant.id,
                day=day_datetime,
                metrics=metrics,
            )
            db.add(usage)

    db.commit()


def get_usage(
    db: Session,
    tenant_id: str,
    start_date: date,
    end_date: date,
) -> list[Dict[str, Any]]:
    """Get usage records for a date range."""
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.min.time()) + timedelta(days=1)

    usage_records = db.execute(
        select(BillingUsage).where(
            BillingUsage.tenant_id == tenant_id,
            BillingUsage.day >= start_datetime,
            BillingUsage.day < end_datetime,
        )
    ).scalars().all()

    return [
        {
            "day": record.day.isoformat(),
            "metrics": record.metrics,
        }
        for record in usage_records
    ]

