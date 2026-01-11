#!/usr/bin/env python3
"""Validate runbook YAML files for syntax and policy compliance."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    print("❌ PyYAML not installed. Install with: pip install pyyaml")
    sys.exit(1)

# Valid tool names from the codebase
VALID_TOOLS = {
    "github.create_issue",
    "github.revert_pr",
    "github.rollback_release",
    "jira.create_issue",
    "jira.comment_issue",
    "jira.transition_issue",
    "k8s.cordon_node",
    "k8s.drain_node",
    "k8s.restart_deployment",
    "k8s.uncordon_node",
    "k8s.check_health",
    "pagerduty.ack",
    "pagerduty.resolve",
    "pagerduty.create_incident",
}

# Valid step types
VALID_STEP_TYPES = {"tool", "llm", "human", "condition", "loop", "trigger"}


def validate_yaml_syntax(file_path: Path) -> tuple[bool, dict[str, Any] | None, str | None]:
    """Validate YAML syntax."""
    try:
        with open(file_path, "r") as f:
            data = yaml.safe_load(f)
        return True, data, None
    except yaml.YAMLError as e:
        return False, None, f"YAML syntax error: {e}"
    except Exception as e:
        return False, None, f"Error reading file: {e}"


def validate_runbook_structure(data: dict[str, Any]) -> list[str]:
    """Validate runbook structure and content."""
    errors = []

    # Check required fields
    if "name" not in data:
        errors.append("Missing required field: 'name'")

    # Validate steps
    if "steps" not in data:
        errors.append("Missing required field: 'steps'")
        return errors

    if not isinstance(data["steps"], list):
        errors.append("'steps' must be a list")
        return errors

    if len(data["steps"]) == 0:
        errors.append("'steps' list cannot be empty")

    # Validate each step
    for idx, step in enumerate(data["steps"]):
        if not isinstance(step, dict):
            errors.append(f"Step {idx + 1} must be a dictionary")
            continue

        if "name" not in step:
            errors.append(f"Step {idx + 1} missing required field: 'name'")

        # Validate tool steps
        if "tool" in step:
            tool_name = step["tool"]
            if tool_name not in VALID_TOOLS:
                errors.append(f"Step {idx + 1}: Invalid tool '{tool_name}'. Valid tools: {', '.join(sorted(VALID_TOOLS))}")

        # Validate step type if present
        if "type" in step:
            step_type = step["type"]
            if step_type not in VALID_STEP_TYPES:
                errors.append(f"Step {idx + 1}: Invalid type '{step_type}'. Valid types: {', '.join(sorted(VALID_STEP_TYPES))}")

        # Validate input/args
        if "input" in step or "args" in step:
            input_data = step.get("input") or step.get("args")
            if not isinstance(input_data, dict):
                errors.append(f"Step {idx + 1}: 'input' or 'args' must be a dictionary")

    return errors


def validate_runbook(file_path: Path) -> tuple[bool, list[str]]:
    """Validate a runbook file."""
    errors = []

    # Check file exists
    if not file_path.exists():
        return False, [f"File not found: {file_path}"]

    # Validate YAML syntax
    valid, data, yaml_error = validate_yaml_syntax(file_path)
    if not valid:
        return False, [yaml_error]

    if data is None:
        return False, ["Empty YAML file"]

    # Validate structure
    structure_errors = validate_runbook_structure(data)
    errors.extend(structure_errors)

    return len(errors) == 0, errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate runbook YAML files")
    parser.add_argument("files", nargs="+", type=Path, help="Runbook YAML files to validate")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as errors")
    args = parser.parse_args()

    all_valid = True
    for file_path in args.files:
        valid, errors = validate_runbook(file_path)
        if valid:
            print(f"✅ {file_path} is valid")
        else:
            print(f"❌ {file_path} has errors:")
            for error in errors:
                print(f"   - {error}")
            all_valid = False

    sys.exit(0 if all_valid else 1)


if __name__ == "__main__":
    main()

