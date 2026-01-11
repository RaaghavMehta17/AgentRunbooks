from __future__ import annotations

JIRA_CREATE_ISSUE_SCHEMA = {
    "type": "object",
    "properties": {
        "project": {"type": "string", "minLength": 1},
        "summary": {"type": "string", "minLength": 1},
        "description": {"type": "string"},
        "issueType": {"type": "string", "minLength": 1},
    },
    "required": ["project", "summary", "issueType"],
    "additionalProperties": False,
}


