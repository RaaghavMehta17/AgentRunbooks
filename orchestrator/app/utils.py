from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any


def json_safe(data: Any) -> Any:
    try:
        json.dumps(data)
        return data
    except TypeError:
        return str(data)


def make_id() -> str:
    return str(uuid.uuid4())


def make_idempotency_key(run_id: str, step_name: str, args: dict[str, Any]) -> str:
    payload = f"{run_id}:{step_name}:{hashlib.sha256(json.dumps(args, sort_keys=True).encode()).hexdigest()}"
    return payload


