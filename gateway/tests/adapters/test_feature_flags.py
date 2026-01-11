from __future__ import annotations

import os
import pytest
from fastapi.testclient import TestClient

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"

from app.main import app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def token(client: TestClient) -> str:
    # Register and login to get token
    client.post(
        "/auth/register",
        json={"email": "test@example.com", "password": "test123"},
    )
    resp = client.post(
        "/auth/login",
        json={"email": "test@example.com", "password": "test123"},
    )
    return resp.json()["access_token"]


def test_feature_flag_list(client: TestClient, token: str):
    """Test listing feature flags."""
    resp = client.get(
        "/feature-flags",
        headers={"authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)


def test_feature_flag_create(client: TestClient, token: str):
    """Test creating a feature flag."""
    resp = client.post(
        "/feature-flags",
        headers={"authorization": f"Bearer {token}"},
        json={"tool": "github.revert_pr", "mode": "real"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["tool"] == "github.revert_pr"
    assert data["mode"] == "real"


def test_feature_flag_update(client: TestClient, token: str):
    """Test updating a feature flag."""
    # Create
    client.post(
        "/feature-flags",
        headers={"authorization": f"Bearer {token}"},
        json={"tool": "github.revert_pr", "mode": "mock"},
    )

    # Update
    resp = client.post(
        "/feature-flags",
        headers={"authorization": f"Bearer {token}"},
        json={"tool": "github.revert_pr", "mode": "real"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["mode"] == "real"


def test_feature_flag_invalid_mode(client: TestClient, token: str):
    """Test creating feature flag with invalid mode."""
    resp = client.post(
        "/feature-flags",
        headers={"authorization": f"Bearer {token}"},
        json={"tool": "github.revert_pr", "mode": "invalid"},
    )
    assert resp.status_code == 400


def test_which_adapter_respects_flag(client: TestClient, token: str):
    """Test that adapter selection respects feature flag."""
    # Set flag to real
    client.post(
        "/feature-flags",
        headers={"authorization": f"Bearer {token}"},
        json={"tool": "github.revert_pr", "mode": "real"},
    )

    # Plan should show real mode
    resp = client.post(
        "/tools/plan",
        headers={"authorization": f"Bearer {token}"},
        json={
            "tool": "github.revert_pr",
            "args": {"owner": "org", "repo": "svc", "pr_number": 123},
            "dryRun": True,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["adapterMode"] == "real"

