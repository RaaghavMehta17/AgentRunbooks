from __future__ import annotations

from typing import Protocol

from .types import AdapterResponse, ToolCall


class Adapter(Protocol):
    async def invoke(self, call: ToolCall) -> AdapterResponse:
        ...


