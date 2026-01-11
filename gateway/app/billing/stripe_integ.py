"""Stripe integration (test mode only)."""

import os
from typing import Dict, Any, Optional
from datetime import datetime, date
from sqlalchemy import select
from sqlalchemy.orm import Session

try:
    import stripe
except ImportError:
    stripe = None

from ..models import Tenant, Invoice, BillingUsage


def get_stripe_client():
    """Get Stripe client (test mode only)."""
    if stripe is None:
        raise RuntimeError("stripe package not installed")
    
    api_key = os.getenv("STRIPE_TEST_KEY")
    if not api_key:
        raise RuntimeError("STRIPE_TEST_KEY not configured")
    
    stripe.api_key = api_key
    return stripe


def create_stripe_customer(db: Session, tenant_id: str) -> Dict[str, Any]:
    """Create a Stripe customer for a tenant."""
    tenant = db.get(Tenant, tenant_id)
    if not tenant:
        raise ValueError(f"Tenant {tenant_id} not found")

    stripe_client = get_stripe_client()

    # Check if customer already exists (store in tenant metadata or separate table)
    # TODO: Cache customer_id in tenant settings
    customer = stripe_client.Customer.create(
        name=tenant.name,
        metadata={"tenant_id": tenant_id},
        description=f"Ops-agents tenant: {tenant.name}",
    )

    return {
        "customer_id": customer.id,
        "tenant_id": tenant_id,
        "created": True,
    }


def create_invoice(
    db: Session,
    tenant_id: str,
    month: str,  # YYYY-MM format
) -> Dict[str, Any]:
    """Create a Stripe invoice for a tenant's monthly usage."""
    tenant = db.get(Tenant, tenant_id)
    if not tenant:
        raise ValueError(f"Tenant {tenant_id} not found")

    # Check if invoice already exists
    existing = db.execute(
        select(Invoice).where(
            Invoice.tenant_id == tenant_id,
            Invoice.month == month,
        )
    ).scalar_one_or_none()

    if existing:
        return {
            "invoice_id": existing.id,
            "stripe_invoice_id": existing.stripe_invoice_id,
            "status": existing.status,
            "amount_usd": existing.amount_usd,
            "payment_link": existing.stripe_payment_link,
        }

    # Aggregate usage for the month
    year, month_num = map(int, month.split("-"))
    start_date = date(year, month_num, 1)
    if month_num == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month_num + 1, 1)

    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.min.time())

    usage_records = db.execute(
        select(BillingUsage).where(
            BillingUsage.tenant_id == tenant_id,
            BillingUsage.day >= start_datetime,
            BillingUsage.day < end_datetime,
        )
    ).scalars().all()

    total_cost = 0.0
    for record in usage_records:
        metrics = record.metrics or {}
        total_cost += metrics.get("total_cost", 0.0)

    # Round to 2 decimal places
    amount_usd = round(total_cost, 2)

    # Create Stripe invoice (test mode)
    stripe_client = get_stripe_client()

    # Get or create customer
    customer = create_stripe_customer(db, tenant_id)
    customer_id = customer["customer_id"]

    # Create payment link (simpler than full invoice for test mode)
    payment_link = stripe_client.PaymentLink.create(
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": f"Ops-agents usage for {month}",
                        "description": f"Usage charges for tenant {tenant.name}",
                    },
                    "unit_amount": int(amount_usd * 100),  # Convert to cents
                },
                "quantity": 1,
            }
        ],
        metadata={"tenant_id": tenant_id, "month": month},
    )

    # Create invoice record
    invoice = Invoice(
        tenant_id=tenant_id,
        month=month,
        amount_usd=amount_usd,
        status="pending",
        stripe_invoice_id=None,  # Using payment link instead
        stripe_payment_link=payment_link.url,
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)

    return {
        "invoice_id": invoice.id,
        "stripe_payment_link": invoice.stripe_payment_link,
        "status": invoice.status,
        "amount_usd": invoice.amount_usd,
    }


def handle_webhook(
    db: Session,
    payload: str,
    signature: str,
) -> Dict[str, Any]:
    """Handle Stripe webhook event."""
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    if not webhook_secret:
        raise RuntimeError("STRIPE_WEBHOOK_SECRET not configured")

    stripe_client = get_stripe_client()

    try:
        event = stripe_client.Webhook.construct_event(
            payload,
            signature,
            webhook_secret,
        )
    except ValueError as e:
        raise ValueError(f"Invalid payload: {e}")
    except stripe.error.SignatureVerificationError as e:
        raise ValueError(f"Invalid signature: {e}")

    # Handle invoice.paid event
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        metadata = session.get("metadata", {})
        tenant_id = metadata.get("tenant_id")
        month = metadata.get("month")

        if tenant_id and month:
            invoice = db.execute(
                select(Invoice).where(
                    Invoice.tenant_id == tenant_id,
                    Invoice.month == month,
                )
            ).scalar_one_or_none()

            if invoice:
                invoice.status = "paid"
                invoice.paid_at = datetime.utcnow()
                db.commit()

                return {"status": "success", "invoice_id": invoice.id}

    return {"status": "ignored", "event_type": event["type"]}

