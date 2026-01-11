from __future__ import annotations

from typing import Any

PLANNER_OUT = {
    "type": "object",
    "properties": {
        "steps": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "tool": {"type": "string"},
                    "args": {"type": "object"},
                },
                "required": ["name", "tool", "args"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["steps"],
    "additionalProperties": False,
}

TOOLCALLER_OUT = {
    "type": "object",
    "properties": {
        "tool": {"type": "string"},
        "args": {"type": "object"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "rationale": {"type": "string"},
    },
    "required": ["tool", "args", "confidence", "rationale"],
    "additionalProperties": False,
}

REVIEWER_OUT = {
    "type": "object",
    "properties": {
        "decision": {"type": "string", "enum": ["allow", "block", "require_approval"]},
        "reasons": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": ["decision", "reasons"],
    "additionalProperties": False,
}

