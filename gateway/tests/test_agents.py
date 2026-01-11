from __future__ import annotations

import pytest

from app.agents.brain import plan_and_review


@pytest.mark.asyncio
async def test_brain_plan_and_review_stubs():
    """Test brain with stubs (no API key) returns valid JSON and decisions."""
    runbook_yaml = """
name: test-runbook
steps:
  - name: ack-page
    tool: pagerduty.ack
    input:
      incident_id: INC123
  - name: rollback
    tool: github.rollback_release
    input:
      repo: org/service
      tag: v1.2.2
"""
    policy_yaml = """
roles:
  - Admin
  - SRE
tool_allowlist:
  Admin: [pagerduty.ack, github.rollback_release]
"""
    context = {"env": "dev", "caller": "test@example.com"}

    result = await plan_and_review(runbook_yaml, policy_yaml, context)

    assert "planned" in result
    assert "usage" in result
    assert isinstance(result["planned"], list)
    assert len(result["planned"]) > 0

    # Check each planned step has required fields
    for step in result["planned"]:
        assert "name" in step
        assert "tool" in step
        assert "args" in step
        assert "decision" in step
        assert step["decision"] in ["allow", "block", "require_approval"]
        assert "reasons" in step
        assert isinstance(step["reasons"], list)

    # Check usage sums
    usage = result["usage"]
    assert "tokens_in" in usage
    assert "tokens_out" in usage
    assert "latency_ms" in usage
    assert "cost_usd" in usage
    assert usage["tokens_in"] >= 0
    assert usage["tokens_out"] >= 0
    assert usage["latency_ms"] >= 0
    assert usage["cost_usd"] >= 0


@pytest.mark.asyncio
async def test_brain_invalid_json_raises():
    """Test brain raises 422 on invalid JSON from LLM."""
    # This would require mocking the provider to return invalid JSON
    # For now, stubs always return valid JSON, so this is a placeholder
    pass

