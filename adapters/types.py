from __future__ import annotations

from typing import Any, Dict, Generic, TypeVar, TypedDict

TIn = TypeVar("TIn")
TOut = TypeVar("TOut")


class ToolCall(TypedDict, total=False):
    name: str
    input: Dict[str, Any]
    dryRun: bool
    idempotencyKey: str | None


class AdapterResponse(TypedDict, total=False):
    output: Dict[str, Any] | None
    audit: Dict[str, Any]


