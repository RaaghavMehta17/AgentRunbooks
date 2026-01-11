from __future__ import annotations

PAGERDUTY_ACK_SCHEMA = {
    "type": "object",
    "properties": {
        "incident_id": {"type": "string", "minLength": 1},
        "note": {"type": "string"},
    },
    "required": ["incident_id"],
    "additionalProperties": False,
}


