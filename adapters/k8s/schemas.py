from __future__ import annotations

K8S_DRAIN_NODE_SCHEMA = {
    "type": "object",
    "properties": {
        "node": {"type": "string", "minLength": 1},
        "evict": {"type": "boolean"},
        "force": {"type": "boolean"},
    },
    "required": ["node"],
    "additionalProperties": False,
}


