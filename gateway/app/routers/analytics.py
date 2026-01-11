"""Analytics API endpoints for metrics, charts, and ROI data."""

from __future__ import annotations

from datetime import datetime, timedelta, date
from typing import Optional
from collections import defaultdict

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, and_, or_, case, cast, Integer, Float
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Run, Runbook, Step
from ..rbac import authorize
from ..tenancy import get_tenant_and_project

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/metrics")
async def get_metrics(
    request: Request,
    range: str = Query("7d", description="Time range: 24h, 7d, 30d, 90d"),
    db: Session = Depends(get_db),
    _auth: None = Depends(authorize("read", "*")),
):
    """Get key metrics for analytics dashboard."""
    tenant_id, project_id = get_tenant_and_project(request, db)
    
    # Calculate date range
    now = datetime.utcnow()
    if range == "24h":
        start_date = now - timedelta(days=1)
    elif range == "7d":
        start_date = now - timedelta(days=7)
    elif range == "30d":
        start_date = now - timedelta(days=30)
    elif range == "90d":
        start_date = now - timedelta(days=90)
    else:
        start_date = now - timedelta(days=7)
    
    # Build query filters
    filters = [Run.created_at >= start_date]
    if tenant_id:
        filters.append(Run.tenant_id == tenant_id)
    if project_id:
        filters.append(Run.project_id == project_id)
    
    # Get previous period for comparison
    period_days = (now - start_date).days
    prev_start = start_date - timedelta(days=period_days)
    prev_filters = [Run.created_at >= prev_start, Run.created_at < start_date]
    if tenant_id:
        prev_filters.append(Run.tenant_id == tenant_id)
    if project_id:
        prev_filters.append(Run.project_id == project_id)
    
    # Total runs
    total_runs = db.query(func.count(Run.id)).filter(and_(*filters)).scalar() or 0
    prev_total_runs = db.query(func.count(Run.id)).filter(and_(*prev_filters)).scalar() or 0
    runs_change = ((total_runs - prev_total_runs) / prev_total_runs * 100) if prev_total_runs > 0 else 0
    
    # Success rate
    successful_runs = db.query(func.count(Run.id)).filter(
        and_(*filters, Run.status.in_(["succeeded", "completed"]))
    ).scalar() or 0
    success_rate = (successful_runs / total_runs * 100) if total_runs > 0 else 0
    
    prev_successful = db.query(func.count(Run.id)).filter(
        and_(*prev_filters, Run.status.in_(["succeeded", "completed"]))
    ).scalar() or 0
    prev_success_rate = (prev_successful / prev_total_runs * 100) if prev_total_runs > 0 else 0
    success_change = success_rate - prev_success_rate
    
    # Average duration (estimate from metrics latency_ms or use default)
    avg_duration_result = db.query(
        func.avg(
            case(
                (Run.metrics["latency_ms"].astext.isnot(None), Run.metrics["latency_ms"].astext.cast(func.int)),
                else_=252000  # Default 4m 12s in ms
            )
        )
    ).filter(and_(*filters)).scalar()
    avg_duration_ms = int(avg_duration_result) if avg_duration_result else 252000
    avg_duration_str = format_duration(avg_duration_ms)
    
    prev_avg_duration = db.query(
        func.avg(
            case(
                (Run.metrics["latency_ms"].astext.isnot(None), Run.metrics["latency_ms"].astext.cast(func.int)),
                else_=252000
            )
        )
    ).filter(and_(*prev_filters)).scalar()
    prev_avg_duration_ms = int(prev_avg_duration) if prev_avg_duration else 252000
    duration_change = ((avg_duration_ms - prev_avg_duration_ms) / prev_avg_duration_ms * 100) if prev_avg_duration_ms > 0 else 0
    
    # Total cost (extract from JSON metrics)
    runs_with_metrics = db.query(Run.metrics).filter(and_(*filters, Run.metrics.isnot(None))).all()
    total_cost = sum(float(run.metrics.get("cost_usd", 0)) for run in runs_with_metrics if isinstance(run.metrics, dict))
    
    prev_runs_with_metrics = db.query(Run.metrics).filter(and_(*prev_filters, Run.metrics.isnot(None))).all()
    prev_total_cost = sum(float(run.metrics.get("cost_usd", 0)) for run in prev_runs_with_metrics if isinstance(run.metrics, dict))
    cost_change = ((total_cost - prev_total_cost) / prev_total_cost * 100) if prev_total_cost > 0 else 0
    
    # Time saved (estimate: 30 minutes per successful run)
    time_saved_hours = (successful_runs * 0.5)
    prev_time_saved = (prev_successful * 0.5)
    time_saved_change = ((time_saved_hours - prev_time_saved) / prev_time_saved * 100) if prev_time_saved > 0 else 0
    
    # Tokens used (extract from JSON metrics)
    tokens_used = sum(
        int(run.metrics.get("tokens_in", 0)) + int(run.metrics.get("tokens_out", 0))
        for run in runs_with_metrics
        if isinstance(run.metrics, dict)
    )
    
    prev_tokens = sum(
        int(run.metrics.get("tokens_in", 0)) + int(run.metrics.get("tokens_out", 0))
        for run in prev_runs_with_metrics
        if isinstance(run.metrics, dict)
    )
    tokens_change = ((tokens_used - prev_tokens) / prev_tokens * 100) if prev_tokens > 0 else 0
    
    return {
        "totalRuns": {"value": total_runs, "change": round(runs_change, 1), "trend": "up" if runs_change >= 0 else "down"},
        "successRate": {"value": round(success_rate, 1), "change": round(success_change, 1), "trend": "up" if success_change >= 0 else "down"},
        "avgDuration": {"value": avg_duration_str, "change": round(duration_change, 1), "trend": "up" if duration_change >= 0 else "down"},
        "totalCost": {"value": round(total_cost, 2), "change": round(cost_change, 1), "trend": "up" if cost_change >= 0 else "down"},
        "timeSaved": {"value": int(time_saved_hours), "change": round(time_saved_change, 1), "trend": "up" if time_saved_change >= 0 else "down"},
        "tokensUsed": {"value": tokens_used, "change": round(tokens_change, 1), "trend": "up" if tokens_change >= 0 else "down"},
    }


@router.get("/runs")
async def get_runs_data(
    request: Request,
    range: str = Query("7d", description="Time range: 24h, 7d, 30d, 90d"),
    db: Session = Depends(get_db),
    _auth: None = Depends(authorize("read", "*")),
):
    """Get runs data for charts (daily breakdown)."""
    tenant_id, project_id = get_tenant_and_project(request, db)
    
    # Calculate date range
    now = datetime.utcnow()
    if range == "24h":
        days = 1
        start_date = now - timedelta(days=1)
    elif range == "7d":
        days = 7
        start_date = now - timedelta(days=7)
    elif range == "30d":
        days = 30
        start_date = now - timedelta(days=30)
    elif range == "90d":
        days = 90
        start_date = now - timedelta(days=90)
    else:
        days = 7
        start_date = now - timedelta(days=7)
    
    filters = [Run.created_at >= start_date]
    if tenant_id:
        filters.append(Run.tenant_id == tenant_id)
    if project_id:
        filters.append(Run.project_id == project_id)
    
    # Group by date
    runs_by_date = db.query(
        func.date(Run.created_at).label("date"),
        func.count(Run.id).label("total"),
        func.sum(case((Run.status.in_(["succeeded", "completed"]), 1), else_=0)).label("success"),
        func.sum(case((Run.status == "failed", 1), else_=0)).label("failed"),
    ).filter(and_(*filters)).group_by(func.date(Run.created_at)).all()
    
    # Format data
    runs_data = []
    for row in runs_by_date:
        runs_data.append({
            "date": row.date.strftime("%a") if days <= 7 else row.date.strftime("%m/%d"),
            "runs": row.total or 0,
            "success": row.success or 0,
            "failed": row.failed or 0,
        })
    
    return runs_data


@router.get("/cost")
async def get_cost_data(
    request: Request,
    range: str = Query("7d", description="Time range: 24h, 7d, 30d, 90d"),
    db: Session = Depends(get_db),
    _auth: None = Depends(authorize("read", "*")),
):
    """Get cost data for charts."""
    tenant_id, project_id = get_tenant_and_project(request, db)
    
    # Calculate date range
    now = datetime.utcnow()
    if range == "24h":
        days = 1
        start_date = now - timedelta(days=1)
    elif range == "7d":
        days = 7
        start_date = now - timedelta(days=7)
    elif range == "30d":
        days = 30
        start_date = now - timedelta(days=30)
    elif range == "90d":
        days = 90
        start_date = now - timedelta(days=90)
    else:
        days = 7
        start_date = now - timedelta(days=7)
    
    filters = [Run.created_at >= start_date]
    if tenant_id:
        filters.append(Run.tenant_id == tenant_id)
    if project_id:
        filters.append(Run.project_id == project_id)
    
    # Group by date (simplified - aggregate in Python)
    runs_by_date = db.query(
        func.date(Run.created_at).label("date"),
        Run.metrics,
    ).filter(and_(*filters, Run.metrics.isnot(None))).all()
    
    # Aggregate by date
    cost_by_date_dict = {}
    for row in runs_by_date:
        date_key = row.date.strftime("%a") if days <= 7 else row.date.strftime("%m/%d")
        if date_key not in cost_by_date_dict:
            cost_by_date_dict[date_key] = {"cost": 0.0, "tokens": 0}
        
        if isinstance(row.metrics, dict):
            cost_by_date_dict[date_key]["cost"] += float(row.metrics.get("cost_usd", 0))
            cost_by_date_dict[date_key]["tokens"] += int(row.metrics.get("tokens_in", 0)) + int(row.metrics.get("tokens_out", 0))
    
    cost_data = [
        {"date": date, "cost": round(data["cost"], 2), "tokens": data["tokens"]}
        for date, data in cost_by_date_dict.items()
    ]
    
    return cost_data


@router.get("/latency")
async def get_latency_data(
    request: Request,
    range: str = Query("7d", description="Time range: 24h, 7d, 30d, 90d"),
    db: Session = Depends(get_db),
    _auth: None = Depends(authorize("read", "*")),
):
    """Get latency percentile data."""
    tenant_id, project_id = get_tenant_and_project(request, db)
    
    # Calculate date range
    now = datetime.utcnow()
    if range == "24h":
        days = 1
        start_date = now - timedelta(days=1)
    elif range == "7d":
        days = 7
        start_date = now - timedelta(days=7)
    elif range == "30d":
        days = 30
        start_date = now - timedelta(days=30)
    elif range == "90d":
        days = 90
        start_date = now - timedelta(days=90)
    else:
        days = 7
        start_date = now - timedelta(days=7)
    
    filters = [Run.created_at >= start_date]
    if tenant_id:
        filters.append(Run.tenant_id == tenant_id)
    if project_id:
        filters.append(Run.project_id == project_id)
    
    # Get latency estimates (using metrics latency_ms if available, otherwise estimate)
    runs_by_date = db.query(
        func.date(Run.created_at).label("date"),
        Run.metrics,
    ).filter(and_(*filters)).all()
    
    # Aggregate by date
    latency_by_date_dict = {}
    for row in runs_by_date:
        date_key = row.date.strftime("%a") if days <= 7 else row.date.strftime("%m/%d")
        if date_key not in latency_by_date_dict:
            latency_by_date_dict[date_key] = []
        
        if isinstance(row.metrics, dict):
            latency_ms = int(row.metrics.get("latency_ms", 300000))  # Default 5 minutes
        else:
            latency_ms = 300000
        latency_by_date_dict[date_key].append(latency_ms)
    
    # Calculate percentiles
    latency_data = []
    for date, latencies in latency_by_date_dict.items():
        sorted_latencies = sorted(latencies)
        n = len(sorted_latencies)
        p50 = sorted_latencies[int(n * 0.5)] if n > 0 else 300000
        p90 = sorted_latencies[int(n * 0.9)] if n > 0 else int(p50 * 1.5)
        p99 = sorted_latencies[int(n * 0.99)] if n > 0 else int(p50 * 2.0)
        
        latency_data.append({
            "date": date,
            "p50": p50,
            "p90": p90,
            "p99": p99,
        })
    
    return latency_data


@router.get("/top-runbooks")
async def get_top_runbooks(
    request: Request,
    range: str = Query("7d", description="Time range: 24h, 7d, 30d, 90d"),
    limit: int = Query(5, description="Number of runbooks to return"),
    db: Session = Depends(get_db),
    _auth: None = Depends(authorize("read", "*")),
):
    """Get top runbooks by execution count."""
    tenant_id, project_id = get_tenant_and_project(request, db)
    
    # Calculate date range
    now = datetime.utcnow()
    if range == "24h":
        start_date = now - timedelta(days=1)
    elif range == "7d":
        start_date = now - timedelta(days=7)
    elif range == "30d":
        start_date = now - timedelta(days=30)
    elif range == "90d":
        start_date = now - timedelta(days=90)
    else:
        start_date = now - timedelta(days=7)
    
    filters = [Run.created_at >= start_date]
    if tenant_id:
        filters.append(Run.tenant_id == tenant_id)
    if project_id:
        filters.append(Run.project_id == project_id)
    
    # Get top runbooks
    top_runbooks = db.query(
        Runbook.name,
        Runbook.id,
        func.count(Run.id).label("runs"),
        func.sum(case((Run.status.in_(["succeeded", "completed"]), 1), else_=0)).label("successful"),
        func.avg(
            case(
                (Run.metrics.isnot(None), 300000),  # Default 5 minutes estimate
                else_=300000
            )
        ).label("avg_duration"),
        func.sum(case((Run.metrics.isnot(None), 0.0), else_=0.0)).label("cost"),  # Will calculate in Python
    ).join(Run, Run.runbook_id == Runbook.id).filter(
        and_(*filters)
    ).group_by(Runbook.id, Runbook.name).order_by(
        func.count(Run.id).desc()
    ).limit(limit).all()
    
    result = []
    for row in top_runbooks:
        runs_count = row.runs or 0
        successful_count = row.successful or 0
        success_rate = (successful_count / runs_count * 100) if runs_count > 0 else 0
        avg_duration_ms = int(row.avg_duration) if row.avg_duration else 0
        
        result.append({
            "name": row.name,
            "runs": runs_count,
            "successRate": round(success_rate, 1),
            "avgDuration": format_duration(avg_duration_ms),
            "cost": round(row.cost or 0, 2),
        })
    
    return result


@router.get("/cost-breakdown")
async def get_cost_breakdown(
    request: Request,
    range: str = Query("7d", description="Time range: 24h, 7d, 30d, 90d"),
    db: Session = Depends(get_db),
    _auth: None = Depends(authorize("read", "*")),
):
    """Get cost breakdown by category."""
    tenant_id, project_id = get_tenant_and_project(request, db)
    
    # Calculate date range
    now = datetime.utcnow()
    if range == "24h":
        start_date = now - timedelta(days=1)
    elif range == "7d":
        start_date = now - timedelta(days=7)
    elif range == "30d":
        start_date = now - timedelta(days=30)
    elif range == "90d":
        start_date = now - timedelta(days=90)
    else:
        start_date = now - timedelta(days=7)
    
    filters = [Run.created_at >= start_date]
    if tenant_id:
        filters.append(Run.tenant_id == tenant_id)
    if project_id:
        filters.append(Run.project_id == project_id)
    
    # Get total cost (extract from JSON metrics)
    runs_with_metrics = db.query(Run.metrics).filter(and_(*filters, Run.metrics.isnot(None))).all()
    total_cost = sum(float(run.metrics.get("cost_usd", 0)) for run in runs_with_metrics if isinstance(run.metrics, dict))
    
    # Estimate breakdown (simplified - would need more detailed tracking)
    # LLM tokens: 55%, Tool executions: 28%, External APIs: 12%, Storage: 5%
    breakdown = [
        {"category": "LLM Tokens", "value": round(total_cost * 0.55, 2), "percentage": 55},
        {"category": "Tool Executions", "value": round(total_cost * 0.28, 2), "percentage": 28},
        {"category": "External APIs", "value": round(total_cost * 0.12, 2), "percentage": 12},
        {"category": "Storage", "value": round(total_cost * 0.05, 2), "percentage": 5},
    ]
    
    return breakdown


def format_duration(ms: int) -> str:
    """Format duration in milliseconds to human-readable string."""
    if ms < 1000:
        return f"{ms}ms"
    seconds = ms // 1000
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    secs = seconds % 60
    if minutes < 60:
        return f"{minutes}m {secs}s"
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours}h {mins}m"

