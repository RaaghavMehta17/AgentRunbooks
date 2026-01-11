from __future__ import annotations

import os
import time
from typing import Any

import httpx
from opentelemetry import trace

from ..types import AdapterResponse, ToolCall

tracer = trace.get_tracer(__name__)


def _get_headers(token: str | None) -> dict[str, str]:
    """Get GitHub API headers."""
    if not token:
        raise RuntimeError("GITHUB_TOKEN required")
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


async def invoke(call: ToolCall) -> AdapterResponse:
    """Real GitHub adapter with multiple tools."""
    tool_name = call.get("name", "")
    payload = call.get("input", {})
    dry_run = call.get("dryRun", True)
    idempotency_key = call.get("idempotencyKey")
    token = os.getenv("GITHUB_TOKEN")

    with tracer.start_as_current_span("github.adapter.invoke") as span:
        span.set_attribute("tool", tool_name)
        span.set_attribute("dry_run", dry_run)

        try:
            if tool_name == "github.rollback_release":
                result = await _rollback_release(payload, dry_run, idempotency_key, token)
            elif tool_name == "github.revert_pr":
                result = await _revert_pr(payload, dry_run, idempotency_key, token)
            elif tool_name == "github.create_issue":
                result = await _create_issue(payload, dry_run, idempotency_key, token)
            else:
                raise ValueError(f"unknown tool: {tool_name}")

            span.set_attribute("success", True)
            return result
        except Exception as e:
            span.set_attribute("success", False)
            span.record_exception(e)
            return {
                "output": None,
                "audit": {
                    "adapter": "github.real",
                    "tool": tool_name,
                    "error": str(e),
                    "dryRun": dry_run,
                },
            }


async def _rollback_release(
    payload: dict[str, Any], dry_run: bool, idempotency_key: str | None, token: str | None
) -> AdapterResponse:
    """Rollback a release: comment in rollback-log issue and create release note entry."""
    repo = payload.get("repo") or os.getenv("GITHUB_DEFAULT_REPO", "")
    tag = payload.get("tag", "")

    if not repo:
        return {"output": None, "audit": {"adapter": "github.real", "tool": "github.rollback_release", "error": "missing repo"}}

    audit: dict[str, Any] = {
        "adapter": "github.real",
        "tool": "github.rollback_release",
        "repo": repo,
        "tag": tag,
        "dryRun": dry_run,
        "idempotencyKey": idempotency_key,
    }

    if dry_run or not token:
        return {
            "output": {
                "ok": True,
                "simulated": True,
                "planned_ops": [
                    f"POST /repos/{repo}/issues (title: rollback-log)",
                    f"POST /repos/{repo}/releases (tag: {tag})",
                ],
            },
            "audit": audit,
        }

    headers = _get_headers(token)
    start = time.perf_counter()

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Find or create rollback-log issue
        issue_number = None
        try:
            # Search for existing rollback-log issue
            search_resp = await client.get(
                f"https://api.github.com/search/issues?q=repo:{repo}+is:issue+title:rollback-log",
                headers=headers,
            )
            if search_resp.status_code == 200:
                issues = search_resp.json().get("items", [])
                if issues:
                    issue_number = issues[0]["number"]
        except Exception:
            pass

        if not issue_number:
            # Create rollback-log issue
            create_resp = await client.post(
                f"https://api.github.com/repos/{repo}/issues",
                headers=headers,
                json={"title": "rollback-log", "body": "Automated rollback log"},
            )
            create_resp.raise_for_status()
            issue_number = create_resp.json()["number"]

        # Comment in issue
        comment_body = f"Rollback requested for tag `{tag}` (idempotencyKey={idempotency_key})"
        comment_resp = await client.post(
            f"https://api.github.com/repos/{repo}/issues/{issue_number}/comments",
            headers=headers,
            json={"body": comment_body},
        )
        comment_resp.raise_for_status()

        # Create release note entry (as a release with prerelease flag or draft)
        release_resp = await client.post(
            f"https://api.github.com/repos/{repo}/releases",
            headers=headers,
            json={
                "tag_name": f"{tag}-rollback",
                "name": f"Rollback: {tag}",
                "body": f"Rollback of {tag} - {comment_body}",
                "draft": True,
            },
        )
        release_resp.raise_for_status()
        release_data = release_resp.json()

        elapsed = time.perf_counter() - start
        audit["elapsed_seconds"] = elapsed
        audit["issue_number"] = issue_number
        audit["release_id"] = release_data.get("id")

        return {
            "output": {
                "ok": True,
                "issue_number": issue_number,
                "issue_url": f"https://github.com/{repo}/issues/{issue_number}",
                "release_id": release_data.get("id"),
                "release_url": release_data.get("html_url"),
            },
            "audit": audit,
        }


async def _revert_pr(
    payload: dict[str, Any], dry_run: bool, idempotency_key: str | None, token: str | None
) -> AdapterResponse:
    """Revert a merged PR by creating a revert PR."""
    owner = payload["owner"]
    repo = payload["repo"]
    pr_number = payload["pr_number"]
    title = payload.get("title")

    audit: dict[str, Any] = {
        "adapter": "github.real",
        "tool": "github.revert_pr",
        "owner": owner,
        "repo": repo,
        "pr_number": pr_number,
        "dryRun": dry_run,
        "idempotencyKey": idempotency_key,
    }

    if dry_run or not token:
        return {
            "output": {
                "ok": True,
                "simulated": True,
                "planned_ops": [
                    f"GET /repos/{owner}/{repo}/pulls/{pr_number}",
                    f"POST /repos/{owner}/{repo}/git/reverts (or create revert PR)",
                ],
            },
            "audit": audit,
        }

    headers = _get_headers(token)
    start = time.perf_counter()

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Get PR details
        pr_resp = await client.get(f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}", headers=headers)
        pr_resp.raise_for_status()
        pr_data = pr_resp.json()

        if not pr_data.get("merged"):
            raise ValueError(f"PR #{pr_number} is not merged, cannot revert")

        merge_commit_sha = pr_data.get("merge_commit_sha")
        if not merge_commit_sha:
            raise ValueError(f"PR #{pr_number} has no merge commit")

        # Try to use GitHub's revert API (if available)
        # Otherwise, create a revert PR manually
        revert_title = title or f"Revert \"{pr_data.get('title', '')}\""
        revert_body = f"Reverts #{pr_number}\n\n{pr_data.get('body', '')}"

        try:
            # Try git revert API (may not be available in all GitHub versions)
            revert_resp = await client.post(
                f"https://api.github.com/repos/{owner}/{repo}/git/reverts",
                headers=headers,
                json={"commit_sha": merge_commit_sha, "title": revert_title, "body": revert_body},
            )
            if revert_resp.status_code == 201:
                revert_data = revert_resp.json()
                elapsed = time.perf_counter() - start
                audit["elapsed_seconds"] = elapsed
                audit["revert_pr_number"] = revert_data.get("number")
                return {
                    "output": {
                        "ok": True,
                        "revert_pr_number": revert_data.get("number"),
                        "revert_pr_url": revert_data.get("html_url"),
                    },
                    "audit": audit,
                }
        except Exception:
            pass

        # Fallback: create revert PR manually
        # Get default branch
        repo_resp = await client.get(f"https://api.github.com/repos/{owner}/{repo}", headers=headers)
        repo_resp.raise_for_status()
        default_branch = repo_resp.json().get("default_branch", "main")

        # Create revert branch and PR
        revert_branch = f"revert-{pr_number}-{merge_commit_sha[:7]}"
        pr_resp = await client.post(
            f"https://api.github.com/repos/{owner}/{repo}/pulls",
            headers=headers,
            json={
                "title": revert_title,
                "body": revert_body,
                "head": revert_branch,
                "base": default_branch,
            },
        )
        pr_resp.raise_for_status()
        pr_data = pr_resp.json()

        elapsed = time.perf_counter() - start
        audit["elapsed_seconds"] = elapsed
        audit["revert_pr_number"] = pr_data.get("number")

        return {
            "output": {
                "ok": True,
                "revert_pr_number": pr_data.get("number"),
                "revert_pr_url": pr_data.get("html_url"),
            },
            "audit": audit,
        }


async def _create_issue(
    payload: dict[str, Any], dry_run: bool, idempotency_key: str | None, token: str | None
) -> AdapterResponse:
    """Create a GitHub issue."""
    repo = payload["repo"]
    title = payload["title"]
    body = payload.get("body", "")

    audit: dict[str, Any] = {
        "adapter": "github.real",
        "tool": "github.create_issue",
        "repo": repo,
        "title": title,
        "dryRun": dry_run,
        "idempotencyKey": idempotency_key,
    }

    if dry_run or not token:
        return {
            "output": {
                "ok": True,
                "simulated": True,
                "planned_ops": [f"POST /repos/{repo}/issues"],
            },
            "audit": audit,
        }

    headers = _get_headers(token)
    if idempotency_key:
        headers["X-Idempotency-Key"] = idempotency_key

    start = time.perf_counter()
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"https://api.github.com/repos/{repo}/issues",
            headers=headers,
            json={"title": title, "body": body},
        )
        resp.raise_for_status()
        data = resp.json()
        elapsed = time.perf_counter() - start

        audit["elapsed_seconds"] = elapsed
        audit["issue_number"] = data.get("number")

        return {
            "output": {
                "ok": True,
                "issue_number": data.get("number"),
                "issue_url": data.get("html_url"),
            },
            "audit": audit,
        }


