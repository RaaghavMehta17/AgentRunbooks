"""Quota checking and enforcement."""

import os
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional, Tuple
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from ..models import BillingUsage, Tenant


class QuotaExceeded(Exception):
    """Raised when hard quota limit is exceeded."""

    def __init__(self, metric: str, limit: float, current: float):
        self.metric = metric
        self.limit = limit
        self.current = current
        super().__init__(f"Quota exceeded for {metric}: {current} > {limit}")


def get_quota_limits() -> Dict[str, Dict[str, float]]:
    """Get quota limits from environment variables."""
    return {
        "tokens": {
            "day_soft": float(os.getenv("BILLING_SOFT_LIMIT_TOKENS_DAY", "200000")),
            "day_hard": float(os.getenv("BILLING_HARD_LIMIT_TOKENS_DAY", "400000")),
            "month_soft": float(os.getenv("BILLING_SOFT_LIMIT_TOKENS_MONTH", "6000000")),
            "month_hard": float(os.getenv("BILLING_HARD_LIMIT_TOKENS_MONTH", "12000000")),
        },
        "cost": {
            "day_soft": float(os.getenv("BILLING_SOFT_LIMIT_COST_DAY", "5")),
            "day_hard": float(os.getenv("BILLING_HARD_LIMIT_COST_DAY", "10")),
            "month_soft": float(os.getenv("BILLING_SOFT_LIMIT_COST_MONTH", "20")),
            "month_hard": float(os.getenv("BILLING_HARD_LIMIT_COST_MONTH", "50")),
        },
        "adapter_calls": {
            "day_soft": float(os.getenv("BILLING_SOFT_LIMIT_ADAPTER_CALLS_DAY", "1000")),
            "day_hard": float(os.getenv("BILLING_HARD_LIMIT_ADAPTER_CALLS_DAY", "2000")),
            "month_soft": float(os.getenv("BILLING_SOFT_LIMIT_ADAPTER_CALLS_MONTH", "30000")),
            "month_hard": float(os.getenv("BILLING_HARD_LIMIT_ADAPTER_CALLS_MONTH", "60000")),
        },
    }


def get_current_usage(
    db: Session,
    tenant_id: str,
    period: str = "day",  # "day" or "month"
) -> Dict[str, float]:
    """Get current usage for tenant for the period."""
    now = datetime.utcnow()
    if period == "day":
        start_date = now.date()
        end_date = start_date + timedelta(days=1)
    else:  # month
        start_date = date(now.year, now.month, 1)
        if now.month == 12:
            end_date = date(now.year + 1, 1, 1)
        else:
            end_date = date(now.year, now.month + 1, 1)

    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.min.time())

    usage_records = db.execute(
        select(BillingUsage).where(
            BillingUsage.tenant_id == tenant_id,
            BillingUsage.day >= start_datetime,
            BillingUsage.day < end_datetime,
        )
    ).scalars().all()

    total_tokens = 0
    total_cost = 0.0
    total_adapter_calls = 0

    for record in usage_records:
        metrics = record.metrics or {}
        total_tokens += metrics.get("tokens_in", 0) + metrics.get("tokens_out", 0)
        total_cost += metrics.get("total_cost", 0.0)
        adapter_calls = metrics.get("adapter_calls", {})
        total_adapter_calls += sum(adapter_calls.values())

    return {
        "tokens": total_tokens,
        "cost": total_cost,
        "adapter_calls": total_adapter_calls,
    }


def check_quota(
    db: Session,
    tenant_id: str,
    projected_usage: Optional[Dict[str, float]] = None,
) -> Tuple[bool, Dict[str, Any]]:
    """
    Check quota and return (is_warning, quota_info).
    
    Returns:
        (is_warning, quota_info) where quota_info contains:
        - warnings: list of metrics exceeding soft limits
        - exceeded: list of metrics exceeding hard limits
        - usage: current usage
        - limits: quota limits
    """
    if not os.getenv("BILLING_ENABLED", "false").lower() == "true":
        return False, {}

    quotas = get_quota_limits()
    usage_day = get_current_usage(db, tenant_id, "day")
    usage_month = get_current_usage(db, tenant_id, "month")

    # Add projected usage if provided
    if projected_usage:
        usage_day["tokens"] = usage_day.get("tokens", 0) + projected_usage.get("tokens", 0)
        usage_day["cost"] = usage_day.get("cost", 0.0) + projected_usage.get("cost", 0.0)
        usage_day["adapter_calls"] = usage_day.get("adapter_calls", 0) + projected_usage.get("adapter_calls", 0)

    warnings = []
    exceeded = []

    # Check day quotas
    for metric in ["tokens", "cost", "adapter_calls"]:
        day_usage = usage_day.get(metric, 0)
        day_soft = quotas[metric]["day_soft"]
        day_hard = quotas[metric]["day_hard"]

        if day_usage >= day_hard:
            exceeded.append({"metric": metric, "period": "day", "limit": day_hard, "current": day_usage})
        elif day_usage >= day_soft * 0.8:  # 80% threshold
            warnings.append({"metric": metric, "period": "day", "limit": day_soft, "current": day_usage})

    # Check month quotas
    for metric in ["tokens", "cost", "adapter_calls"]:
        month_usage = usage_month.get(metric, 0)
        month_soft = quotas[metric]["month_soft"]
        month_hard = quotas[metric]["month_hard"]

        if month_usage >= month_hard:
            exceeded.append({"metric": metric, "period": "month", "limit": month_hard, "current": month_usage})
        elif month_usage >= month_soft * 0.8:  # 80% threshold
            warnings.append({"metric": metric, "period": "month", "limit": month_soft, "current": month_usage})

    is_warning = len(warnings) > 0

    quota_info = {
        "warnings": warnings,
        "exceeded": exceeded,
        "usage": {
            "day": usage_day,
            "month": usage_month,
        },
        "limits": quotas,
    }

    return is_warning, quota_info


def enforce_quota(
    db: Session,
    tenant_id: str,
    projected_usage: Optional[Dict[str, float]] = None,
) -> None:
    """Check quota and raise QuotaExceeded if hard limit exceeded."""
    is_warning, quota_info = check_quota(db, tenant_id, projected_usage)

    if quota_info.get("exceeded"):
        exceeded = quota_info["exceeded"][0]  # First exceeded metric
        raise QuotaExceeded(
            metric=exceeded["metric"],
            limit=exceeded["limit"],
            current=exceeded["current"],
        )

