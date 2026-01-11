from __future__ import annotations

import time

from ..types import AdapterResponse, ToolCall


async def invoke(call: ToolCall) -> AdapterResponse:
    time.sleep(0.05)
    return {
        "output": {"ok": True, "simulated": True},
        "audit": {
            "adapter": "github.mock",
            "tool": call.get("name"),
            "input": call.get("input"),
            "dryRun": call.get("dryRun", True),
            "idempotencyKey": call.get("idempotencyKey"),
        },
    }


