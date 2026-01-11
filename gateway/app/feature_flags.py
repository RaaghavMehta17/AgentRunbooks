from __future__ import annotations

import os
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import SessionLocal
from .models import FeatureFlag


def which_adapter(tool: str, request_headers: dict[str, str] | None = None) -> str:
    """
    Determine which adapter to use (real or mock) for a tool.
    Priority: X-Adapter-Real header > DB flag > env flag > default (mock)
    """
    # Check header override first
    if request_headers:
        x_adapter_real = request_headers.get("X-Adapter-Real")
        if x_adapter_real:
            namespace = tool.split(".")[0]
            if x_adapter_real == namespace:
                return "real"

    # Check DB flag
    with SessionLocal() as db:
        flag = db.get(FeatureFlag, tool)
        if flag and flag.mode in ("real", "mock"):
            return flag.mode

    # Check env flag
    env_key = f"ADAPTER_FLAG_{tool}"
    env_value = os.getenv(env_key, "").lower()
    if env_value in ("real", "mock"):
        return env_value

    # Default to mock for safety
    return "mock"


def get_all_flags() -> dict[str, str]:
    """Get all feature flags (env + DB)."""
    flags: dict[str, str] = {}

    # Load from env
    for key, value in os.environ.items():
        if key.startswith("ADAPTER_FLAG_"):
            tool = key.replace("ADAPTER_FLAG_", "")
            flags[tool] = value.lower() if value.lower() in ("real", "mock") else "mock"

    # Override with DB flags
    with SessionLocal() as db:
        db_flags = db.scalars(select(FeatureFlag)).all()
        for flag in db_flags:
            flags[flag.tool] = flag.mode

    return flags

