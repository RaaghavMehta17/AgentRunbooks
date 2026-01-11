from __future__ import annotations

import os
from typing import Any

from fastapi import Request, Response
from itsdangerous import URLSafeTimedSerializer

SESSION_SECRET = os.getenv("SESSION_SECRET", "dev_session_secret_change_in_production")
SESSION_COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", "ops_agents_session")
SESSION_TTL_MIN = int(os.getenv("SESSION_TTL_MIN", "60"))

_serializer = URLSafeTimedSerializer(SESSION_SECRET)


def set_session_cookie(response: Response, payload: dict[str, Any], ttl_min: int = SESSION_TTL_MIN) -> None:
    """Set a signed session cookie."""
    token = _serializer.dumps(payload, salt="session")
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=ttl_min * 60,
        httponly=True,
        secure=os.getenv("SESSION_SECURE", "false").lower() == "true",  # Set in prod behind HTTPS
        samesite="lax",
    )


def get_session(request: Request) -> dict[str, Any] | None:
    """Get and verify session cookie."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        return None

    try:
        payload = _serializer.loads(token, salt="session", max_age=SESSION_TTL_MIN * 60)
        return payload
    except Exception:
        return None


def clear_session(response: Response) -> None:
    """Clear session cookie."""
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        httponly=True,
        samesite="lax",
    )

