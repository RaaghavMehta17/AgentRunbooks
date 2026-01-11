from __future__ import annotations

import base64
import os
from typing import Any

import httpx
from opentelemetry import trace

from ..types import AdapterResponse, ToolCall

tracer = trace.get_tracer(__name__)

JIRA_BASE_URL = os.getenv("JIRA_BASE_URL", "")
JIRA_USER_EMAIL = os.getenv("JIRA_USER_EMAIL", "")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN", "")
JIRA_PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY", "SRE")


def _get_auth_header() -> dict[str, str]:
    """Get Basic auth header for Jira."""
    if not JIRA_USER_EMAIL or not JIRA_API_TOKEN:
        raise RuntimeError("JIRA_USER_EMAIL and JIRA_API_TOKEN required")
    token = base64.b64encode(f"{JIRA_USER_EMAIL}:{JIRA_API_TOKEN}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


async def invoke(call: ToolCall) -> AdapterResponse:
    """Real Jira adapter with safe-by-default execution."""
    tool = call.get("name", "")
    args = call.get("input", {})
    dry_run = call.get("dryRun", True)
    idempotency_key = call.get("idempotencyKey")

    with tracer.start_as_current_span("jira.adapter.invoke") as span:
        span.set_attribute("tool", tool)
        span.set_attribute("dry_run", dry_run)
        span.set_attribute("idempotency_key", idempotency_key or "")

        if not JIRA_BASE_URL:
            return {
                "output": None,
                "audit": {
                    "adapter": "jira.real",
                    "tool": tool,
                    "error": "JIRA_BASE_URL not configured",
                    "dryRun": dry_run,
                },
            }

        try:
            if tool == "jira.create_issue":
                result = await _create_issue(args, dry_run, idempotency_key)
            elif tool == "jira.transition_issue":
                result = await _transition_issue(args, dry_run, idempotency_key)
            elif tool == "jira.comment_issue":
                result = await _comment_issue(args, dry_run, idempotency_key)
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
                    "adapter": "jira.real",
                    "tool": tool,
                    "error": str(e),
                    "dryRun": dry_run,
                },
            }


async def _create_issue(args: dict[str, Any], dry_run: bool, idempotency_key: str | None) -> AdapterResponse:
    """Create a Jira issue."""
    project_key = args.get("project", JIRA_PROJECT_KEY)
    summary = args["summary"]
    description = args.get("description", "")
    issue_type = args.get("issuetype", "Task")

    if dry_run:
        return {
            "output": {
                "ok": True,
                "simulated": True,
                "planned_ops": [
                    f"POST {JIRA_BASE_URL}/rest/api/3/issue",
                    f"Body: {{project: {project_key}, summary: {summary}, issuetype: {issue_type}}}",
                ],
                "issue_key": f"{project_key}-SIMULATED",
            },
            "audit": {
                "adapter": "jira.real",
                "tool": "jira.create_issue",
                "project": project_key,
                "summary": summary,
                "dryRun": True,
                "idempotencyKey": idempotency_key,
            },
        }

    # Real execution
    headers = _get_auth_header()
    if idempotency_key:
        headers["X-Idempotency-Key"] = idempotency_key

    payload = {
        "fields": {
            "project": {"key": project_key},
            "summary": summary,
            "description": {"type": "doc", "version": 1, "content": [{"type": "paragraph", "content": [{"type": "text", "text": description}]}]},
            "issuetype": {"name": issue_type},
        }
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{JIRA_BASE_URL}/rest/api/3/issue",
            json=payload,
            headers=headers,
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()

    return {
        "output": {"ok": True, "issue_key": data["key"], "issue_id": data["id"]},
        "audit": {
            "adapter": "jira.real",
            "tool": "jira.create_issue",
            "issue_key": data["key"],
            "project": project_key,
            "idempotencyKey": idempotency_key,
        },
    }


async def _transition_issue(args: dict[str, Any], dry_run: bool, idempotency_key: str | None) -> AdapterResponse:
    """Transition a Jira issue."""
    issue_key = args["issue_key"]
    transition_name = args["transition_name"]

    if dry_run:
        return {
            "output": {
                "ok": True,
                "simulated": True,
                "planned_ops": [
                    f"GET {JIRA_BASE_URL}/rest/api/3/issue/{issue_key}/transitions",
                    f"POST {JIRA_BASE_URL}/rest/api/3/issue/{issue_key}/transitions (transition: {transition_name})",
                ],
            },
            "audit": {
                "adapter": "jira.real",
                "tool": "jira.transition_issue",
                "issue_key": issue_key,
                "transition": transition_name,
                "dryRun": True,
                "idempotencyKey": idempotency_key,
            },
        }

    # Real execution: first get transitions, then find matching one
    headers = _get_auth_header()
    if idempotency_key:
        headers["X-Idempotency-Key"] = idempotency_key

    async with httpx.AsyncClient() as client:
        # Get available transitions
        response = await client.get(
            f"{JIRA_BASE_URL}/rest/api/3/issue/{issue_key}/transitions",
            headers=headers,
            timeout=30.0,
        )
        response.raise_for_status()
        transitions_data = response.json()

        # Find transition by name
        transition_id = None
        for trans in transitions_data.get("transitions", []):
            if trans["name"].lower() == transition_name.lower():
                transition_id = trans["id"]
                break

        if not transition_id:
            raise ValueError(f"transition '{transition_name}' not found for issue {issue_key}")

        # Execute transition
        response = await client.post(
            f"{JIRA_BASE_URL}/rest/api/3/issue/{issue_key}/transitions",
            json={"transition": {"id": transition_id}},
            headers=headers,
            timeout=30.0,
        )
        response.raise_for_status()

    return {
        "output": {"ok": True, "issue_key": issue_key, "transition": transition_name},
        "audit": {
            "adapter": "jira.real",
            "tool": "jira.transition_issue",
            "issue_key": issue_key,
            "transition": transition_name,
            "idempotencyKey": idempotency_key,
        },
    }


async def _comment_issue(args: dict[str, Any], dry_run: bool, idempotency_key: str | None) -> AdapterResponse:
    """Add a comment to a Jira issue."""
    issue_key = args["issue_key"]
    body = args["body"]

    if dry_run:
        return {
            "output": {
                "ok": True,
                "simulated": True,
                "planned_ops": [
                    f"POST {JIRA_BASE_URL}/rest/api/3/issue/{issue_key}/comment",
                    f"Body: {{body: {body[:50]}...}}",
                ],
            },
            "audit": {
                "adapter": "jira.real",
                "tool": "jira.comment_issue",
                "issue_key": issue_key,
                "body_preview": body[:50] if body else "",
                "dryRun": True,
                "idempotencyKey": idempotency_key,
            },
        }

    # Real execution
    headers = _get_auth_header()
    if idempotency_key:
        headers["X-Idempotency-Key"] = idempotency_key

    payload = {
        "body": {
            "type": "doc",
            "version": 1,
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": body}]}],
        }
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{JIRA_BASE_URL}/rest/api/3/issue/{issue_key}/comment",
            json=payload,
            headers=headers,
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()

    return {
        "output": {"ok": True, "issue_key": issue_key, "comment_id": data["id"]},
        "audit": {
            "adapter": "jira.real",
            "tool": "jira.comment_issue",
            "issue_key": issue_key,
            "comment_id": data["id"],
            "idempotencyKey": idempotency_key,
        },
    }

