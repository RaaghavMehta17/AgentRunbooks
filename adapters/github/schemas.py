from __future__ import annotations

GITHUB_ROLLBACK_SCHEMA = {
    "type": "object",
    "properties": {
        "repo": {"type": "string", "minLength": 3},
        "tag": {"type": "string", "minLength": 1},
    },
    "required": ["repo", "tag"],
    "additionalProperties": False,
}


