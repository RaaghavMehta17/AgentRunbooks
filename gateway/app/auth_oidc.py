from __future__ import annotations

import base64
import hashlib
import os
import secrets
from typing import Any
from urllib.parse import urlencode

from authlib.integrations.httpx_client import AsyncOAuth2Client
from authlib.jose import jwt

OIDC_ENABLED = os.getenv("OIDC_ENABLED", "false").lower() == "true"
OIDC_ISSUER = os.getenv("OIDC_ISSUER", "")
OIDC_CLIENT_ID = os.getenv("OIDC_CLIENT_ID", "")
OIDC_CLIENT_SECRET = os.getenv("OIDC_CLIENT_SECRET", "")
OIDC_REDIRECT_URI = os.getenv("OIDC_REDIRECT_URI", "http://localhost:8000/auth/oidc/callback")
OIDC_SCOPES = os.getenv("OIDC_SCOPES", "openid profile email groups").split()
OIDC_GROUPS_CLAIM = os.getenv("OIDC_GROUPS_CLAIM", "groups")
OIDC_ROLE_MAP_STR = os.getenv("OIDC_ROLE_MAP", "{}")

# Parse role map
try:
    import json

    OIDC_ROLE_MAP: dict[str, list[str]] = json.loads(OIDC_ROLE_MAP_STR)
except Exception:
    OIDC_ROLE_MAP = {}


_oidc_client: AsyncOAuth2Client | None = None
_oidc_metadata: dict[str, Any] | None = None


def _generate_pkce() -> tuple[str, str]:
    """Generate PKCE code verifier and challenge."""
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip("=")
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).decode().rstrip("=")
    return code_verifier, code_challenge


async def get_oidc_client() -> AsyncOAuth2Client:
    """Get or create OIDC client with discovery."""
    global _oidc_client, _oidc_metadata

    if _oidc_client and _oidc_metadata:
        return _oidc_client

    if not OIDC_ISSUER:
        raise RuntimeError("OIDC_ISSUER not configured")

    # Discover OIDC configuration
    async with AsyncOAuth2Client() as client:
        metadata_url = f"{OIDC_ISSUER}/.well-known/openid-configuration"
        resp = await client.get(metadata_url)
        resp.raise_for_status()
        _oidc_metadata = resp.json()

    _oidc_client = AsyncOAuth2Client(
        client_id=OIDC_CLIENT_ID,
        client_secret=OIDC_CLIENT_SECRET,
        redirect_uri=OIDC_REDIRECT_URI,
        scope=" ".join(OIDC_SCOPES),
    )

    return _oidc_client


def build_authorize_redirect(state: str, nonce: str) -> tuple[str, str]:
    """Build OIDC authorize URL with PKCE. Returns (url, code_verifier)."""
    if not _oidc_metadata:
        raise RuntimeError("OIDC metadata not loaded")

    code_verifier, code_challenge = _generate_pkce()

    auth_endpoint = _oidc_metadata["authorization_endpoint"]
    params = {
        "response_type": "code",
        "client_id": OIDC_CLIENT_ID,
        "redirect_uri": OIDC_REDIRECT_URI,
        "scope": " ".join(OIDC_SCOPES),
        "state": state,
        "nonce": nonce,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }

    url = f"{auth_endpoint}?{urlencode(params)}"
    return url, code_verifier


async def exchange_code_for_token(code: str, code_verifier: str) -> dict[str, Any]:
    """Exchange authorization code for tokens."""
    client = await get_oidc_client()
    token_endpoint = _oidc_metadata["token_endpoint"]

    resp = await client.post(
        token_endpoint,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": OIDC_REDIRECT_URI,
            "code_verifier": code_verifier,
        },
    )
    resp.raise_for_status()
    return resp.json()


async def verify_id_token(id_token: str, nonce: str) -> dict[str, Any]:
    """Verify and decode ID token."""
    if not _oidc_metadata:
        raise RuntimeError("OIDC metadata not loaded")

    # Get JWKS for verification
    jwks_url = _oidc_metadata["jwks_uri"]
    import httpx

    async with httpx.AsyncClient() as client:
        jwks_resp = await client.get(jwks_url)
        jwks_resp.raise_for_status()
        jwks = jwks_resp.json()

    # Verify token
    claims = jwt.decode(
        id_token,
        jwks,
        claims_options={
            "iss": {"essential": True, "value": OIDC_ISSUER},
            "aud": {"essential": True, "value": OIDC_CLIENT_ID},
            "nonce": {"essential": True, "value": nonce},
        },
    )
    claims.validate()

    return claims


def extract_user_info(id_token_claims: dict[str, Any]) -> dict[str, Any]:
    """Extract user info from ID token claims."""
    email = id_token_claims.get("email") or id_token_claims.get("sub")
    subject = id_token_claims.get("sub")
    groups = id_token_claims.get(OIDC_GROUPS_CLAIM, [])

    if not isinstance(groups, list):
        groups = []

    return {
        "email": email,
        "subject": subject,
        "groups": groups,
    }


def map_groups_to_roles(groups: list[str]) -> list[str]:
    """Map IdP groups to platform roles using OIDC_ROLE_MAP."""
    roles: set[str] = set()

    for group in groups:
        group_lower = group.lower()
        for role, role_groups in OIDC_ROLE_MAP.items():
            for role_group in role_groups:
                # Case-insensitive matching
                if role_group.lower() == group_lower:
                    roles.add(role)
                # Support regex if starts/ends with ^/$
                elif role_group.startswith("^") and role_group.endswith("$"):
                    import re

                    pattern = role_group[1:-1]
                    if re.match(pattern, group, re.IGNORECASE):
                        roles.add(role)

    return sorted(list(roles))

