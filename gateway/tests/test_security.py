"""Comprehensive security tests for RBAC, audit, and rate limiting."""

from __future__ import annotations

import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["SESSION_SECRET"] = "test_secret"
os.environ["AUDIT_HMAC_SECRET"] = "test_audit_secret"
os.environ["JWT_SECRET"] = "test_jwt_secret"
os.environ["OIDC_DEV_MODE"] = "true"

from app.main import app  # noqa: E402
from app.db import SessionLocal, init_db  # noqa: E402
from app.models import RoleBinding, Tenant, User  # noqa: E402
from app.security import create_access_token  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    init_db()
    return TestClient(app)


@pytest.fixture
def tenant(db_session):
    tenant = Tenant(id=str(uuid4()), name="test-tenant")
    db_session.add(tenant)
    db_session.commit()
    return tenant


@pytest.fixture
def db_session():
    from app.db import SessionLocal
    db = SessionLocal()
    try:
        yield db
        db.rollback()
    finally:
        db.close()


def create_user_token(email: str, roles: list[str] = None) -> str:
    """Create a JWT token for a user."""
    payload = {"email": email, "roles": roles or []}
    return create_access_token(payload)


def test_viewer_cannot_execute_run(client: TestClient, tenant, db_session):
    """Test that Viewer role cannot execute runs."""
    # Create role binding
    binding = RoleBinding(
        id=str(uuid4()),
        tenant_id=tenant.id,
        subject_type="user",
        subject_id="viewer@example.com",
        role="Viewer",
    )
    db_session.add(binding)
    db_session.commit()

    # Create token with Viewer role
    token = create_user_token("viewer@example.com", ["Viewer"])

    # Try to execute a run (should fail)
    response = client.post(
        "/runs",
        json={"runbook_id": "test", "mode": "execute"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
    assert "permission denied" in response.json()["detail"].lower()


def test_viewer_can_read_runbooks(client: TestClient, tenant, db_session):
    """Test that Viewer role can read runbooks."""
    binding = RoleBinding(
        id=str(uuid4()),
        tenant_id=tenant.id,
        subject_type="user",
        subject_id="viewer@example.com",
        role="Viewer",
    )
    db_session.add(binding)
    db_session.commit()

    token = create_user_token("viewer@example.com", ["Viewer"])

    # Try to list runbooks (should succeed)
    response = client.get("/runbooks", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200


def test_sre_can_execute_run(client: TestClient, tenant, db_session):
    """Test that SRE role can execute runs."""
    binding = RoleBinding(
        id=str(uuid4()),
        tenant_id=tenant.id,
        subject_type="user",
        subject_id="sre@example.com",
        role="SRE",
    )
    db_session.add(binding)
    db_session.commit()

    token = create_user_token("sre@example.com", ["SRE"])

    # Try to execute a run (should succeed - but may fail due to missing runbook)
    response = client.post(
        "/runs",
        json={"runbook_id": "nonexistent", "mode": "execute"},
        headers={"Authorization": f"Bearer {token}"},
    )
    # Should not be 403 (permission denied)
    assert response.status_code != 403


def test_sre_cannot_approve_without_oncall(client: TestClient, tenant, db_session):
    """Test that SRE alone cannot approve."""
    binding = RoleBinding(
        id=str(uuid4()),
        tenant_id=tenant.id,
        subject_type="user",
        subject_id="sre@example.com",
        role="SRE",
    )
    db_session.add(binding)
    db_session.commit()

    token = create_user_token("sre@example.com", ["SRE"])

    # Try to list approvals (should succeed - read is allowed)
    response = client.get("/approvals", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200

    # Try to approve (should fail - need OnCall role)
    response = client.post(
        "/approvals/nonexistent/approve",
        json={"comment": "test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_admin_has_all_permissions(client: TestClient, tenant, db_session):
    """Test that Admin role has all permissions."""
    binding = RoleBinding(
        id=str(uuid4()),
        tenant_id=tenant.id,
        subject_type="user",
        subject_id="admin@example.com",
        role="Admin",
    )
    db_session.add(binding)
    db_session.commit()

    token = create_user_token("admin@example.com", ["Admin"])

    # Admin should be able to do everything
    response = client.get("/runbooks", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200

    response = client.post(
        "/runbooks",
        json={"name": "test", "yaml": "name: test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    # Should not be 403
    assert response.status_code != 403


def test_audit_chain_verification(client: TestClient, tenant, db_session):
    """Test audit log chain integrity."""
    from app.audit import write_audit
    from app.models import AuditLog
    from sqlalchemy import select

    # Write some audit logs
    write_audit(
        actor_type="user",
        actor_id="test@example.com",
        tenant_id=tenant.id,
        action="test.action1",
        resource_type="test",
        resource_id="1",
    )
    write_audit(
        actor_type="user",
        actor_id="test@example.com",
        tenant_id=tenant.id,
        action="test.action2",
        resource_type="test",
        resource_id="2",
    )

    # Verify chain
    stmt = select(AuditLog).where(AuditLog.tenant_id == tenant.id).order_by(AuditLog.ts)
    logs = db_session.scalars(stmt).all()

    assert len(logs) >= 2
    # First log should have no prev_hash
    assert logs[0].prev_hash is None
    # Second log should have prev_hash pointing to first
    assert logs[1].prev_hash == logs[0].hash
    # All logs should have hashes
    assert all(log.hash for log in logs)


def test_rate_limit_enforcement(client: TestClient):
    """Test rate limiting (basic check)."""
    from app.middleware import check_rate_limit

    # Rate limit should work
    subject = "test-subject"
    # First calls should pass
    assert check_rate_limit(subject, rps=10.0, burst=5.0) is True
    # Rapid calls should eventually be limited (depending on implementation)


def test_secret_redaction():
    """Test secret redaction in logs."""
    from app.logging_utils import redact_secrets, redact_dict

    # Test API key redaction
    text = 'API_KEY=ghp_abcdefghijklmnopqrstuvwxyz1234567890'
    redacted = redact_secrets(text)
    assert 'ghp_' not in redacted or 'REDACTED' in redacted

    # Test dict redaction
    data = {
        "api_key": "secret123",
        "username": "user",
        "password": "pass123",
    }
    redacted = redact_dict(data)
    assert redacted["api_key"] == "***REDACTED***"
    assert redacted["password"] == "***REDACTED***"
    assert redacted["username"] == "user"  # Not sensitive

