from __future__ import annotations

import os
from typing import Any

import httpx
from opentelemetry import trace

from ..types import AdapterResponse, ToolCall

tracer = trace.get_tracer(__name__)

PD_API_TOKEN = os.getenv("PD_API_TOKEN", "")
PD_DEFAULT_SERVICE_ID = os.getenv("PD_DEFAULT_SERVICE_ID", "")
PD_API_BASE = "https://api.pagerduty.com"


def _get_auth_header() -> dict[str, str]:
    """Get auth header for PagerDuty."""
    if not PD_API_TOKEN:
        raise RuntimeError("PD_API_TOKEN required")
    return {
        "Authorization": f"Token token={PD_API_TOKEN}",
        "Accept": "application/vnd.pagerduty+json;version=2",
        "Content-Type": "application/json",
    }


async def invoke(call: ToolCall) -> AdapterResponse:
    """Real PagerDuty adapter with safe-by-default execution."""
    tool = call.get("name", "")
    args = call.get("input", {})
    dry_run = call.get("dryRun", True)
    idempotency_key = call.get("idempotencyKey")

    with tracer.start_as_current_span("pagerduty.adapter.invoke") as span:
        span.set_attribute("tool", tool)
        span.set_attribute("dry_run", dry_run)
        span.set_attribute("idempotency_key", idempotency_key or "")

        if not PD_API_TOKEN:
            return {
                "output": None,
                "audit": {
                    "adapter": "pagerduty.real",
                    "tool": tool,
                    "error": "PD_API_TOKEN not configured",
                    "dryRun": dry_run,
                },
            }

        try:
            if tool == "pagerduty.ack":
                result = await _ack_incident(args, dry_run, idempotency_key)
            elif tool == "pagerduty.resolve":
                result = await _resolve_incident(args, dry_run, idempotency_key)
            elif tool == "pagerduty.create_incident":
                result = await _create_incident(args, dry_run, idempotency_key)
            else:
                raise ValueError(f"unknown tool: {tool}")

            span.set_attribute("success", True)
            return result
        except Exception as e:
            span.set_attribute("success", False)
            span.record_exception(e)
            return {
                "output": None,
                "audit": {
                    "adapter": "pagerduty.real",
                    "tool": tool,
                    "error": str(e),
                    "dryRun": dry_run,
                },
            }


async def _ack_incident(args: dict[str, Any], dry_run: bool, idempotency_key: str | None) -> AdapterResponse:
    """Acknowledge a PagerDuty incident."""
    incident_id = args["incident_id"]

    if dry_run:
        return {
            "output": {
                "ok": True,
                "simulated": True,
                "planned_ops": [
                    f"PUT {PD_API_BASE}/incidents/{incident_id}",
                    "Body: {type: incident_reference, status: acknowledged}",
                ],
            },
            "audit": {
                "adapter": "pagerduty.real",
                "tool": "pagerduty.ack",
                "incident_id": incident_id,
                "dryRun": True,
                "idempotencyKey": idempotency_key,
            },
        }

    # Real execution
    headers = _get_auth_header()
    if idempotency_key:
        headers["X-Idempotency-Key"] = idempotency_key

    payload = {
        "incident": {
            "type": "incident_reference",
            "status": "acknowledged",
        }
    }

    async with httpx.AsyncClient() as client:
        response = await client.put(
            f"{PD_API_BASE}/incidents/{incident_id}",
            json=payload,
            headers=headers,
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()

    return {
        "output": {"ok": True, "incident_id": incident_id, "status": "acknowledged"},
        "audit": {
            "adapter": "pagerduty.real",
            "tool": "pagerduty.ack",
            "incident_id": incident_id,
            "idempotencyKey": idempotency_key,
        },
    }


async def _resolve_incident(args: dict[str, Any], dry_run: bool, idempotency_key: str | None) -> AdapterResponse:
    """Resolve a PagerDuty incident."""
    incident_id = args["incident_id"]

    if dry_run:
        return {
            "output": {
                "ok": True,
                "simulated": True,
                "planned_ops": [
                    f"PUT {PD_API_BASE}/incidents/{incident_id}",
                    "Body: {type: incident_reference, status: resolved}",
                ],
            },
            "audit": {
                "adapter": "pagerduty.real",
                "tool": "pagerduty.resolve",
                "incident_id": incident_id,
                "dryRun": True,
                "idempotencyKey": idempotency_key,
            },
        }

    # Real execution
    headers = _get_auth_header()
    if idempotency_key:
        headers["X-Idempotency-Key"] = idempotency_key

    payload = {
        "incident": {
            "type": "incident_reference",
            "status": "resolved",
        }
    }

    async with httpx.AsyncClient() as client:
        response = await client.put(
            f"{PD_API_BASE}/incidents/{incident_id}",
            json=payload,
            headers=headers,
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()

    return {
        "output": {"ok": True, "incident_id": incident_id, "status": "resolved"},
        "audit": {
            "adapter": "pagerduty.real",
            "tool": "pagerduty.resolve",
            "incident_id": incident_id,
            "idempotencyKey": idempotency_key,
        },
    }


async def _create_incident(args: dict[str, Any], dry_run: bool, idempotency_key: str | None) -> AdapterResponse:
    """Create a PagerDuty incident."""
    service_id = args.get("service_id", PD_DEFAULT_SERVICE_ID)
    title = args["title"]
    body = args.get("body", "")

    if not service_id:
        raise ValueError("service_id required (or set PD_DEFAULT_SERVICE_ID)")

    if dry_run:
        return {
            "output": {
                "ok": True,
                "simulated": True,
                "planned_ops": [
                    f"POST {PD_API_BASE}/incidents",
                    f"Body: {{service: {{id: {service_id}, type: service_reference}}, title: {title}}}",
                ],
                "incident_id": "SIMULATED",
            },
            "audit": {
                "adapter": "pagerduty.real",
                "tool": "pagerduty.create_incident",
                "service_id": service_id,
                "title": title,
                "dryRun": True,
                "idempotencyKey": idempotency_key,
            },
        }

    # Real execution
    headers = _get_auth_header()
    if idempotency_key:
        headers["X-Idempotency-Key"] = idempotency_key

    payload = {
        "incident": {
            "type": "incident",
            "title": title,
            "service": {
                "id": service_id,
                "type": "service_reference",
            },
            "body": {
                "type": "incident_body",
                "details": body,
            },
        }
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{PD_API_BASE}/incidents",
            json=payload,
            headers=headers,
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()

    return {
        "output": {"ok": True, "incident_id": data["incident"]["id"], "incident_number": data["incident"].get("incident_number")},
        "audit": {
            "adapter": "pagerduty.real",
            "tool": "pagerduty.create_incident",
            "incident_id": data["incident"]["id"],
            "service_id": service_id,
            "idempotencyKey": idempotency_key,
        },
    }

