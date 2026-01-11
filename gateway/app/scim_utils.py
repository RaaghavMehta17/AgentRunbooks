from __future__ import annotations

from typing import Any

SCIM_USER_SCHEMAS = ["urn:ietf:params:scim:schemas:core:2.0:User"]
SCIM_GROUP_SCHEMAS = ["urn:ietf:params:scim:schemas:core:2.0:Group"]


def build_scim_user(user: Any, email: str, external_id: str | None = None, active: bool = True) -> dict[str, Any]:
    """Build SCIM User resource JSON."""
    return {
        "schemas": SCIM_USER_SCHEMAS,
        "id": external_id or user.id if hasattr(user, "id") else "",
        "userName": email,
        "name": {
            "givenName": getattr(user, "given_name", ""),
            "familyName": getattr(user, "family_name", ""),
        },
        "active": active and not (getattr(user, "is_disabled", False) if hasattr(user, "is_disabled") else False),
        "emails": [{"value": email, "primary": True}],
        "meta": {
            "resourceType": "User",
            "created": getattr(user, "created_at", "").isoformat() if hasattr(user, "created_at") and user.created_at else "",
            "lastModified": getattr(user, "last_login_at", "").isoformat() if hasattr(user, "last_login_at") and user.last_login_at else "",
        },
    }


def build_scim_group(group: Any, external_id: str | None = None, members: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Build SCIM Group resource JSON."""
    return {
        "schemas": SCIM_GROUP_SCHEMAS,
        "id": external_id or group.id if hasattr(group, "id") else "",
        "displayName": group.display_name if hasattr(group, "display_name") else "",
        "members": members or [],
        "meta": {
            "resourceType": "Group",
            "created": getattr(group, "created_at", "").isoformat() if hasattr(group, "created_at") and group.created_at else "",
        },
    }


def parse_scim_patch(operations: list[dict[str, Any]]) -> dict[str, Any]:
    """Parse SCIM PATCH operations into add/remove/replace actions."""
    result: dict[str, Any] = {"add": {}, "remove": {}, "replace": {}}

    for op in operations:
        op_type = op.get("op", "").lower()
        path = op.get("path", "")
        value = op.get("value")

        if op_type == "add":
            if path == "members":
                result["add"]["members"] = value or []
            else:
                result["add"][path] = value
        elif op_type == "remove":
            if path == "members":
                # Remove specific members
                result["remove"]["members"] = value or []
            else:
                result["remove"][path] = True
        elif op_type == "replace":
            if path == "active":
                result["replace"]["active"] = value
            elif path == "members":
                result["replace"]["members"] = value
            else:
                result["replace"][path] = value

    return result


def parse_scim_filter(filter_str: str) -> dict[str, Any] | None:
    """Parse SCIM filter string like 'userName eq "email@example.com"'."""
    if not filter_str:
        return None

    # Simple parser for common filters
    parts = filter_str.split(" eq ", 1)
    if len(parts) == 2:
        attr = parts[0].strip()
        value = parts[1].strip().strip('"').strip("'")
        return {"attribute": attr, "value": value}

    return None

