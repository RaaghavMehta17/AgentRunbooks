from __future__ import annotations

import pytest

from app.policy_engine import decide


def test_precondition_allow():
    """Test precondition allows step when condition matches."""
    preconditions = [
        {"when": "context.env == 'prod'", "then": "require_approval", "step": "drain-node"}
    ]
    step = {"name": "drain-node", "tool": "k8s.drain_node"}
    context = {"env": "prod", "caller": "admin@example.com"}
    
    result = decide(preconditions, step, context)
    assert result == "require_approval"


def test_precondition_block():
    """Test precondition blocks step when condition matches."""
    preconditions = [
        {"when": "context.env == 'prod'", "then": "block", "step": "drain-node"}
    ]
    step = {"name": "drain-node", "tool": "k8s.drain_node"}
    context = {"env": "prod"}
    
    result = decide(preconditions, step, context)
    assert result == "block"


def test_precondition_no_match():
    """Test precondition returns None when condition doesn't match."""
    preconditions = [
        {"when": "context.env == 'prod'", "then": "block", "step": "drain-node"}
    ]
    step = {"name": "drain-node", "tool": "k8s.drain_node"}
    context = {"env": "dev"}
    
    result = decide(preconditions, step, context)
    assert result is None


def test_precondition_step_filter():
    """Test precondition only applies to specified step."""
    preconditions = [
        {"when": "context.env == 'prod'", "then": "block", "step": "drain-node"}
    ]
    step = {"name": "rollback", "tool": "github.rollback_release"}
    context = {"env": "prod"}
    
    result = decide(preconditions, step, context)
    assert result is None  # Should not match different step


def test_precondition_complex_expr():
    """Test precondition with and/or operators."""
    preconditions = [
        {"when": "context.env == 'prod' and context.caller == 'admin'", "then": "require_approval"}
    ]
    step = {"name": "drain-node"}
    context = {"env": "prod", "caller": "admin"}
    
    result = decide(preconditions, step, context)
    assert result == "require_approval"


def test_budget_enforcement_skips_steps():
    """Test that budget enforcement skips remaining steps."""
    # This would be tested in integration tests with actual runs
    pass

