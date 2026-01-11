from __future__ import annotations

import time
from collections import defaultdict
from typing import Callable

from fastapi import Request, Response, status
from prometheus_client import Counter
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import SessionLocal
from .models import APIKey, User
from .security import decode_access_token, verify_api_key
from .sessions import get_session

rate_limit_dropped_total = Counter("rate_limit_dropped_total", "Rate limit drops", ["subject"])

# In-memory token bucket (per subject)
buckets: dict[str, dict[str, float]] = defaultdict(lambda: {"tokens": 0.0, "last_refill": time.time()})

RATE_LIMIT_DEFAULT_RPS = float(__import__("os").getenv("RATE_LIMIT_DEFAULT_RPS", "5"))
RATE_LIMIT_BURST = float(__import__("os").getenv("RATE_LIMIT_BURST", "20"))


def resolve_api_key(key: str) -> tuple[str | None, str | None, str | None]:
    """Resolve API key to tenant_id and api_key_id. Returns (tenant_id, authn_method, api_key_id)."""
    with SessionLocal() as db:
        stmt = select(APIKey).where(APIKey.is_active == True)
        keys = db.scalars(stmt).all()
        for api_key in keys:
            if verify_api_key(key, api_key.hashed_key):
                # Update last_used_at
                from datetime import datetime, timezone

                api_key.last_used_at = datetime.now(timezone.utc)
                db.commit()
                return (api_key.tenant_id, "apikey", api_key.id)
    return (None, None, None)


def check_rate_limit(subject: str, rps: float = RATE_LIMIT_DEFAULT_RPS, burst: float = RATE_LIMIT_BURST) -> bool:
    """Check if request is within rate limit. Returns True if allowed."""
    now = time.time()
    bucket = buckets[subject]

    # Refill tokens
    elapsed = now - bucket["last_refill"]
    bucket["tokens"] = min(burst, bucket["tokens"] + elapsed * rps)
    bucket["last_refill"] = now

    # Check if we have tokens
    if bucket["tokens"] >= 1.0:
        bucket["tokens"] -= 1.0
        return True
    return False


async def auth_middleware(request: Request, call_next: Callable) -> Response:
    """Authenticate request via JWT, session cookie, or API key."""
    # Try API key first
    api_key = request.headers.get("X-API-Key")
    if api_key:
        tenant_id, authn, api_key_id = resolve_api_key(api_key)
        if tenant_id:
            request.state.tenant_id = tenant_id
            request.state.authn = authn
            request.state.api_key_id = api_key_id
            # Rate limit by API key
            if not check_rate_limit(f"apikey:{api_key[:8]}"):
                rate_limit_dropped_total.labels(subject=f"apikey:{api_key[:8]}").inc()
                return Response(
                    content='{"detail":"rate limit exceeded"}',
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    headers={"Retry-After": "1"},
                    media_type="application/json",
                )
        else:
            return Response(
                content='{"detail":"invalid api key"}',
                status_code=status.HTTP_401_UNAUTHORIZED,
                media_type="application/json",
            )
    else:
        # Try JWT from Authorization header
        auth_header = request.headers.get("Authorization", "")
        token = None
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]

        # Try session cookie
        session_data = get_session(request)

        # Prefer JWT for API calls, session for UI
        if token:
            payload = decode_access_token(token)
            if payload:
                user_id = payload.get("sub")
                # Check if user is disabled
                with SessionLocal() as db:
                    from .models import User
                    user = db.get(User, user_id)
                    if user and user.is_disabled:
                        return Response(
                            content='{"detail":"user account disabled"}',
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            media_type="application/json",
                        )
                request.state.user_id = user_id
                request.state.user_email = payload.get("email")
                request.state.user_roles = payload.get("roles", [])
                request.state.tenant_id = "default"
                request.state.authn = "jwt"
        elif session_data:
            user_id = session_data.get("user_id")
            # Check if user is disabled
            if user_id:
                with SessionLocal() as db:
                    from .models import User
                    user = db.get(User, user_id)
                    if user and user.is_disabled:
                        # Clear session
                        response = Response(
                            content='{"detail":"user account disabled"}',
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            media_type="application/json",
                        )
                        from .sessions import clear_session
                        clear_session(response)
                        return response
            request.state.user_id = user_id
            request.state.user_email = session_data.get("email")
            request.state.user_roles = session_data.get("roles", [])
            request.state.tenant_id = "default"
            request.state.authn = "session"

        # Default to anonymous if no auth
        if not hasattr(request.state, "user_id"):
            request.state.user_id = "anonymous"
            request.state.user_email = None
            request.state.user_roles = []
            request.state.tenant_id = "default"
            request.state.authn = "anonymous"

        # Rate limit by user
        user_id = getattr(request.state, "user_id", "anonymous")
        if not check_rate_limit(f"user:{user_id}"):
            rate_limit_dropped_total.labels(subject=f"user:{user_id}").inc()
            return Response(
                content='{"detail":"rate limit exceeded"}',
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                headers={"Retry-After": "1"},
                media_type="application/json",
            )

    response = await call_next(request)
    return response

