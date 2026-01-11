"""Utilities for secure logging with secret redaction."""

from __future__ import annotations

import re
from typing import Any

# Common secret patterns
SECRET_PATTERNS = [
    # API Keys
    (r'(?i)(api[_-]?key|apikey)\s*[:=]\s*["\']?([a-zA-Z0-9_\-]{20,})["\']?', r'\1=***REDACTED***'),
    (r'(?i)(token)\s*[:=]\s*["\']?([a-zA-Z0-9_\-]{20,})["\']?', r'\1=***REDACTED***'),
    # GitHub tokens
    (r'ghp_[a-zA-Z0-9]{36}', 'ghp_***REDACTED***'),
    (r'gho_[a-zA-Z0-9]{36}', 'gho_***REDACTED***'),
    (r'ghu_[a-zA-Z0-9]{36}', 'ghu_***REDACTED***'),
    (r'ghs_[a-zA-Z0-9]{36}', 'ghs_***REDACTED***'),
    (r'ghr_[a-zA-Z0-9]{76}', 'ghr_***REDACTED***'),
    # JWT tokens
    (r'eyJ[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+', '***JWT_REDACTED***'),
    # Passwords
    (r'(?i)(password|passwd|pwd)\s*[:=]\s*["\']?([^"\'\s]+)["\']?', r'\1=***REDACTED***'),
    (r'(?i)(secret)\s*[:=]\s*["\']?([^"\'\s]{10,})["\']?', r'\1=***REDACTED***'),
    # AWS keys
    (r'AKIA[0-9A-Z]{16}', 'AKIA***REDACTED***'),
    (r'(?i)(aws[_-]?secret[_-]?access[_-]?key)\s*[:=]\s*["\']?([a-zA-Z0-9/+=]{40})["\']?', r'\1=***REDACTED***'),
    # Private keys
    (r'-----BEGIN[ A-Z]+PRIVATE KEY-----[\s\S]*?-----END[ A-Z]+PRIVATE KEY-----', '-----BEGIN PRIVATE KEY-----\n***REDACTED***\n-----END PRIVATE KEY-----'),
    # Database URLs with passwords
    (r'://([^:]+):([^@]+)@', r'://\1:***REDACTED***@'),
]


def redact_secrets(text: str) -> str:
    """Redact secrets from text string."""
    if not text:
        return text
    
    redacted = text
    for pattern, replacement in SECRET_PATTERNS:
        redacted = re.sub(pattern, replacement, redacted)
    
    return redacted


def redact_dict(data: dict[str, Any], sensitive_keys: list[str] | None = None) -> dict[str, Any]:
    """Redact sensitive values from dictionary."""
    if sensitive_keys is None:
        sensitive_keys = [
            "api_key", "apiKey", "token", "password", "secret", "auth",
            "authorization", "apikey", "access_token", "refresh_token",
            "private_key", "privateKey", "secret_key", "secretKey",
            "aws_secret_access_key", "github_token", "jira_api_token",
            "pagerduty_api_key", "openai_api_key", "anthropic_api_key",
        ]
    
    redacted = {}
    for key, value in data.items():
        key_lower = key.lower()
        if any(sensitive in key_lower for sensitive in sensitive_keys):
            redacted[key] = "***REDACTED***"
        elif isinstance(value, dict):
            redacted[key] = redact_dict(value, sensitive_keys)
        elif isinstance(value, str) and len(value) > 20:
            # Also check value content for secrets
            redacted[key] = redact_secrets(value)
        else:
            redacted[key] = value
    
    return redacted


def safe_log_message(message: str) -> str:
    """Create a safe log message by redacting secrets."""
    return redact_secrets(message)

