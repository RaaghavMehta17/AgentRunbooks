from __future__ import annotations

import os
import pytest
from fastapi.testclient import TestClient

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["OIDC_DEV_MODE"] = "true"
os.environ["SESSION_SECRET"] = "test_secret"

from app.main import app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_dev_login(client: TestClient):
    """Test dev login sets session cookie."""
    resp = client.post(
        "/auth/oidc/dev-login",
        json={"email": "sre@example.com", "groups": ["sre", "oncall"]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["user"]["email"] == "sre@example.com"
    assert "ops_agents_session" in resp.cookies


def test_dev_login_with_roles(client: TestClient):
    """Test dev login with explicit roles."""
    resp = client.post(
        "/auth/oidc/dev-login",
        json={"email": "admin@example.com", "groups": [], "roles": ["Admin", "SRE"]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "Admin" in data["user"]["roles"]
    assert "SRE" in data["user"]["roles"]


def test_session_cookie_auth(client: TestClient):
    """Test authenticated endpoint using session cookie."""
    # Login first
    login_resp = client.post(
        "/auth/oidc/dev-login",
        json={"email": "sre@example.com", "groups": ["sre"]},
    )
    assert login_resp.status_code == 200
    cookie = login_resp.cookies.get("ops_agents_session")

    # Use cookie for authenticated request
    resp = client.get("/policies", cookies={"ops_agents_session": cookie})
    assert resp.status_code == 200


def test_map_groups_to_roles():
    """Test group to role mapping."""
    from app.auth_oidc import map_groups_to_roles

    os.environ["OIDC_ROLE_MAP"] = '{"SRE":["sre","oncall"],"Admin":["admins"]}'

    # Reload module to pick up new env
    import importlib
    import app.auth_oidc

    importlib.reload(app.auth_oidc)

    roles = app.auth_oidc.map_groups_to_roles(["sre", "oncall"])
    assert "SRE" in roles

    roles = app.auth_oidc.map_groups_to_roles(["admins"])
    assert "Admin" in roles


def test_logout(client: TestClient):
    """Test logout clears session."""
    # Login first
    login_resp = client.post(
        "/auth/oidc/dev-login",
        json={"email": "test@example.com", "groups": []},
    )
    assert login_resp.status_code == 200

    # Logout
    logout_resp = client.post("/auth/logout")
    assert logout_resp.status_code == 200
    # Cookie should be deleted (max_age=0)
    assert "ops_agents_session" in logout_resp.cookies

