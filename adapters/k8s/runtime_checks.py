from __future__ import annotations

import json
import os
from typing import Any


def assert_namespace_allowed(namespace: str) -> None:
    """Assert namespace is in allowlist."""
    allowlist_str = os.getenv("K8S_NAMESPACE_ALLOWLIST", "[]")
    try:
        allowlist = json.loads(allowlist_str)
    except Exception:
        allowlist = []
    
    if allowlist and namespace not in allowlist:
        raise ValueError(f"namespace '{namespace}' not in allowlist: {allowlist}")


def assert_env_allowed(labels: dict[str, Any] | None) -> None:
    """Assert environment label is in allowed list."""
    if not labels:
        return
    
    env_key = os.getenv("K8S_ENV_LABEL_KEY", "cluster.env")
    allowed_str = os.getenv("K8S_ENV_ALLOWED", "[]")
    try:
        allowed = json.loads(allowed_str)
    except Exception:
        allowed = []
    
    if not allowed:
        return  # No restrictions if allowlist is empty
    
    env_value = labels.get(env_key)
    if env_value and env_value not in allowed:
        raise ValueError(
            f"environment '{env_value}' (from label {env_key}) not in allowed list: {allowed}"
        )


def requires_approval_for_env(labels: dict[str, Any] | None) -> bool:
    """Check if environment requires approval (soft check, doesn't raise)."""
    if not labels:
        return False
    
    env_key = os.getenv("K8S_ENV_LABEL_KEY", "cluster.env")
    allowed_str = os.getenv("K8S_ENV_ALLOWED", "[]")
    try:
        allowed = json.loads(allowed_str)
    except Exception:
        allowed = []
    
    if not allowed:
        return False
    
    env_value = labels.get(env_key)
    if env_value and env_value not in allowed:
        return True
    
    return False

