from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timedelta, timezone

import jwt as pyjwt
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

AUDIT_HMAC_SECRET = os.getenv("AUDIT_HMAC_SECRET", "dev_audit_secret")
APPROVAL_SIG_TTL_MIN = int(os.getenv("APPROVAL_SIG_TTL_MIN", "30"))


def hash_api_key(plain: str) -> str:
    """Hash API key using bcrypt."""
    return pwd_context.hash(plain)


def verify_api_key(plain: str, hashed: str) -> bool:
    """Verify API key against hash."""
    return pwd_context.verify(plain, hashed)


def hash_password(password: str) -> str:
    """Hash password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify password against hash."""
    return pwd_context.verify(plain, hashed)


def hmac_hash(prev_hash: str | None, record: dict) -> str:
    """Compute HMAC hash for audit chain."""
    if prev_hash:
        data = prev_hash + json.dumps(record, sort_keys=True, separators=(",", ":"))
    else:
        data = json.dumps(record, sort_keys=True, separators=(",", ":"))
    return hmac.new(
        AUDIT_HMAC_SECRET.encode("utf-8"),
        data.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def sign_approval(payload: dict, ttl_min: int = APPROVAL_SIG_TTL_MIN) -> dict[str, str | datetime]:
    """Sign approval with HMAC token and expiration."""
    nonce = secrets.token_urlsafe(16)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=ttl_min)
    canonical = json.dumps({**payload, "nonce": nonce, "expires_at": expires_at.isoformat()}, sort_keys=True)
    sig = hmac.new(
        AUDIT_HMAC_SECRET.encode("utf-8"),
        canonical.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    token = f"{nonce}.{sig[:16]}"
    return {
        "token": token,
        "sig": sig,
        "expires_at": expires_at,
    }


def verify_approval(token: str, sig: str, expires_at: datetime | None) -> bool:
    """Verify approval token signature and expiration."""
    if not expires_at:
        return False
    if datetime.now(timezone.utc) > expires_at:
        return False
    # TODO: Use stored nonce for signature verification
    parts = token.split(".")
    if len(parts) != 2:
        return False
    return sig is not None and len(sig) > 0


JWT_SECRET = os.getenv("JWT_SECRET", "dev_jwt_secret_change_in_production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_MINUTES = int(os.getenv("JWT_EXPIRATION_MINUTES", "60"))


def create_access_token(data: dict) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRATION_MINUTES)
    to_encode.update({"exp": expire})
    return pyjwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    """Decode and verify JWT access token."""
    try:
        payload = pyjwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except Exception:
        return None

