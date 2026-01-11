from __future__ import annotations

import json
import os
import secrets
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..auth_oidc import (
    OIDC_ENABLED,
    build_authorize_redirect,
    exchange_code_for_token,
    extract_user_info,
    map_groups_to_roles,
    verify_id_token,
)
from ..db import get_db
from ..models import IdentityProvider, User, UserIdentity
from ..sessions import clear_session, get_session, set_session_cookie
from ..security import create_access_token

router = APIRouter()

OIDC_DEV_MODE = os.getenv("OIDC_DEV_MODE", "false").lower() == "true"


class DevLoginRequest(BaseModel):
    email: str
    groups: list[str] = []
    roles: list[str] | None = None


@router.get("/auth/oidc/login")
async def oidc_login(
    redirect: str = Query(default="/"),
    request: Request = None,
    response: Response = None,
) -> Response:
    """Initiate OIDC login flow."""
    if not OIDC_ENABLED:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="OIDC not enabled")

    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)

    try:
        url, code_verifier = build_authorize_redirect(state, nonce)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"OIDC configuration error: {e}"
        )

    # Store state, nonce, code_verifier, and redirect in signed cookie
    from ..sessions import set_session_cookie

    set_session_cookie(
        response,
        {
            "oidc_state": state,
            "oidc_nonce": nonce,
            "oidc_code_verifier": code_verifier,
            "oidc_redirect": redirect,
        },
        ttl_min=10,  # Short-lived for OAuth state
    )

    return Response(status_code=302, headers={"Location": url})


@router.get("/auth/oidc/callback")
async def oidc_callback(
    code: str = Query(...),
    state: str = Query(...),
    request: Request = None,
    db: Session = Depends(get_db),
) -> Response:
    """Handle OIDC callback."""
    if not OIDC_ENABLED:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="OIDC not enabled")

    # Get stored state from session
    session_data = get_session(request)
    if not session_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="no session found")

    stored_state = session_data.get("oidc_state")
    stored_nonce = session_data.get("oidc_nonce")
    stored_code_verifier = session_data.get("oidc_code_verifier")
    redirect_uri = session_data.get("oidc_redirect", "/")

    if stored_state != state:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid state")

    # Exchange code for tokens
    try:
        token_response = await exchange_code_for_token(code, stored_code_verifier)
        id_token = token_response["id_token"]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"token exchange failed: {e}"
        )

    # Verify ID token
    try:
        claims = await verify_id_token(id_token, stored_nonce)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"token verification failed: {e}")

    # Extract user info
    user_info = extract_user_info(claims)
    email = user_info["email"]
    subject = user_info["subject"]
    groups = user_info["groups"]

    # Get or create identity provider
    issuer = os.getenv("OIDC_ISSUER", "")
    provider = db.scalar(select(IdentityProvider).where(IdentityProvider.issuer == issuer))
    if not provider:
        provider = IdentityProvider(
            name=os.getenv("OIDC_PROVIDER_NAME", "default"),
            issuer=issuer,
            client_id=os.getenv("OIDC_CLIENT_ID", ""),
        )
        db.add(provider)
        db.flush()

    # Find or create user
    user = db.scalar(select(User).where(User.email == email))
    if not user:
        user = User(email=email, password_hash=None)
        db.add(user)
        db.flush()

    # Find or create user identity
    user_identity = db.scalar(
        select(UserIdentity).where(
            UserIdentity.provider_id == provider.id, UserIdentity.subject == subject
        )
    )
    if not user_identity:
        user_identity = UserIdentity(
            user_id=user.id,
            provider_id=provider.id,
            subject=subject,
            email=email,
            groups=groups,
        )
        db.add(user_identity)
    else:
        user_identity.groups = groups
        user_identity.email = email

    # Update user last login
    user.last_login_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(user)
    db.refresh(user_identity)

    # Map groups to roles
    roles = map_groups_to_roles(groups)

    # Create JWT
    access_token = create_access_token(data={"sub": user.id, "email": email, "roles": roles})

    # Set session cookie
    response = Response(status_code=302, headers={"Location": redirect_uri})
    set_session_cookie(
        response,
        {
            "user_id": user.id,
            "email": email,
            "roles": roles,
        },
    )

    # Audit log
    write_audit(
        actor_type="user",
        actor_id=email,
        tenant_id="default",
        action="auth.oidc.login",
        resource_type="user",
        resource_id=user.id,
        payload={
            "provider": provider.name,
            "groups": groups,
            "roles": roles,
        },
    )

    # Add JWT to response header for API clients
    response.headers["X-Access-Token"] = access_token

    return response


@router.post("/auth/logout")
async def logout(response: Response) -> dict[str, str]:
    """Logout and clear session."""
    clear_session(response)
    return {"message": "logged out"}


@router.post("/auth/oidc/dev-login", status_code=status.HTTP_200_OK)
async def dev_login(
    payload: DevLoginRequest,
    request: Request = None,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Dev login endpoint (only when OIDC_DEV_MODE=true)."""
    if not OIDC_DEV_MODE:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="dev login not enabled")

    # Find or create user
    user = db.scalar(select(User).where(User.email == payload.email))
    if not user:
        user = User(email=payload.email, password_hash=None)
        db.add(user)
        db.flush()

    # Map groups to roles or use provided roles
    if payload.roles:
        roles = payload.roles
    else:
        roles = map_groups_to_roles(payload.groups)

    # Update last login
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)

    # Create JWT
    access_token = create_access_token(data={"sub": user.id, "email": user.email, "roles": roles})

    # Set session cookie (response will be returned)
    response_data = {
        "access_token": access_token,
        "user": {
            "id": user.id,
            "email": user.email,
            "roles": roles,
        },
    }
    response = Response(content=json.dumps(response_data), media_type="application/json")
    set_session_cookie(
        response,
        {
            "user_id": user.id,
            "email": user.email,
            "roles": roles,
        },
    )

    # Audit log
    write_audit(
        actor_type="user",
        actor_id=user.email,
        tenant_id="default",
        action="auth.oidc.dev_login",
        resource_type="user",
        resource_id=user.id,
        payload={"groups": payload.groups, "roles": roles},
    )

    return response

