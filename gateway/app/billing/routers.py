"""Billing API routes."""

from __future__ import annotations

import json
from datetime import datetime, date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, Header, status
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..db import get_db
from ..models import Invoice, Tenant
from ..rbac import authorize
from ..tenancy import get_tenant_and_project
from .metering import get_usage, aggregate_daily_usage
from .quotas import check_quota, enforce_quota, QuotaExceeded
from .stripe_integ import create_stripe_customer, create_invoice, handle_webhook, get_stripe_client

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/usage")
async def get_usage_endpoint(
    request: Request,
    tenant_id: Optional[str] = None,
    range: str = "month",  # "day", "week", "month"
    db: Session = Depends(get_db),
    _auth: None = Depends(authorize("read", "*")),
):
    """Get usage for tenant (Admin only or own tenant)."""
    # Get tenant from request or parameter
    if not tenant_id:
        resolved_tenant_id, _ = get_tenant_and_project(request, db)
        tenant_id = resolved_tenant_id

    now = datetime.utcnow()
    if range == "day":
        start_date = now.date()
        end_date = start_date
    elif range == "week":
        start_date = now.date() - timedelta(days=7)
        end_date = now.date()
    else:  # month
        start_date = date(now.year, now.month, 1)
        end_date = now.date()

    usage_records = get_usage(db, tenant_id, start_date, end_date)

    # Aggregate totals
    totals = {
        "tokens_in": 0,
        "tokens_out": 0,
        "steps": 0,
        "adapter_calls": {},
        "llm_cost": 0.0,
        "total_cost": 0.0,
    }

    for record in usage_records:
        metrics = record.get("metrics", {})
        totals["tokens_in"] += metrics.get("tokens_in", 0)
        totals["tokens_out"] += metrics.get("tokens_out", 0)
        totals["steps"] += metrics.get("steps", 0)
        totals["llm_cost"] += metrics.get("llm_cost", 0.0)
        totals["total_cost"] += metrics.get("total_cost", 0.0)

        # Merge adapter calls
        for adapter, count in metrics.get("adapter_calls", {}).items():
            totals["adapter_calls"][adapter] = totals["adapter_calls"].get(adapter, 0) + count

    return {
        "tenant_id": tenant_id,
        "range": range,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "usage": usage_records,
        "totals": totals,
    }


@router.get("/quotas")
async def get_quotas(
    request: Request,
    db: Session = Depends(get_db),
    _auth: None = Depends(authorize("read", "*")),
):
    """Get quota status for tenant."""
    tenant_id, _ = get_tenant_and_project(request, db)
    is_warning, quota_info = check_quota(db, tenant_id)

    return quota_info


@router.post("/stripe/create-customer")
async def create_customer_endpoint(
    request: Request,
    tenant_id: str,
    db: Session = Depends(get_db),
    _auth: None = Depends(authorize("write", "*")),
):
    """Create a Stripe customer for tenant."""
    try:
        result = create_stripe_customer(db, tenant_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stripe/invoice")
async def create_invoice_endpoint(
    request: Request,
    tenant_id: str,
    month: str,  # YYYY-MM
    db: Session = Depends(get_db),
    _auth: None = Depends(authorize("write", "*")),
):
    """Create a Stripe invoice for tenant's monthly usage."""
    try:
        result = create_invoice(db, tenant_id, month)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/invoices")
async def list_invoices(
    request: Request,
    tenant_id: Optional[str] = None,
    db: Session = Depends(get_db),
    _auth: None = Depends(authorize("read", "*")),
):
    """List invoices for tenant."""
    if not tenant_id:
        resolved_tenant_id, _ = get_tenant_and_project(request, db)
        tenant_id = resolved_tenant_id

    from sqlalchemy import select
    invoices = db.execute(
        select(Invoice).where(Invoice.tenant_id == tenant_id).order_by(Invoice.created_at.desc())
    ).scalars().all()

    return {
        "tenant_id": tenant_id,
        "invoices": [
            {
                "id": inv.id,
                "month": inv.month,
                "amount_usd": inv.amount_usd,
                "status": inv.status,
                "stripe_payment_link": inv.stripe_payment_link,
                "created_at": inv.created_at.isoformat() if inv.created_at else None,
                "paid_at": inv.paid_at.isoformat() if inv.paid_at else None,
            }
            for inv in invoices
        ],
    }


@router.post("/stripe/webhook")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db),
    stripe_signature: str = Header(..., alias="stripe-signature"),
):
    """Handle Stripe webhook events."""
    payload = await request.body()
    payload_str = payload.decode('utf-8')

    try:
        result = handle_webhook(db, payload_str, stripe_signature)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

