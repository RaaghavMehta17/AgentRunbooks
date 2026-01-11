from __future__ import annotations

import os
import pytest
from httpx import AsyncClient

# Use TestClient for compatibility with existing test setup
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


def test_github_revert_pr_plan(client: TestClient, token: str):
    """Test planning a GitHub revert PR (mock by default)."""
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
    assert data["willCall"] is True
    assert data["tool"] == "github.revert_pr"
    assert data["dryRun"] is True
    assert data["adapterMode"] == "mock"  # Default to mock


def test_github_revert_pr_invoke_mock(client: TestClient, token: str):
    """Test invoking GitHub revert PR with mock adapter."""
    resp = client.post(
        "/tools/invoke",
        headers={"authorization": f"Bearer {token}"},
        json={
            "tool": "github.revert_pr",
            "args": {"owner": "org", "repo": "svc", "pr_number": 123},
            "dryRun": True,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "output" in data
    assert "audit" in data
    assert data["audit"]["adapter"] == "github.mock"


def test_github_create_issue_plan(client: TestClient, token: str):
    """Test planning a GitHub create issue."""
    resp = client.post(
        "/tools/plan",
        headers={"authorization": f"Bearer {token}"},
        json={
            "tool": "github.create_issue",
            "args": {"repo": "org/svc", "title": "Test Issue", "body": "Test body"},
            "dryRun": True,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["willCall"] is True
    assert data["tool"] == "github.create_issue"


def test_github_create_issue_invoke_mock(client: TestClient, token: str):
    """Test invoking GitHub create issue with mock adapter."""
    resp = client.post(
        "/tools/invoke",
        headers={"authorization": f"Bearer {token}"},
        json={
            "tool": "github.create_issue",
            "args": {"repo": "org/svc", "title": "Test Issue"},
            "dryRun": True,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "output" in data
    assert "audit" in data


@pytest.mark.skipif(
    not __import__("os").getenv("GITHUB_TOKEN"), reason="GITHUB_TOKEN not set"
)
def test_github_revert_pr_real(client: TestClient, token: str):
    """Test invoking GitHub revert PR with real adapter (requires token)."""
    # Set feature flag to real
    client.post(
        "/feature-flags",
        headers={"authorization": f"Bearer {token}"},
        json={"tool": "github.revert_pr", "mode": "real"},
    )

    resp = client.post(
        "/tools/invoke",
        headers={"authorization": f"Bearer {token}"},
        json={
            "tool": "github.revert_pr",
            "args": {"owner": "org", "repo": "svc", "pr_number": 123},
            "dryRun": True,  # Still dry-run for safety
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "output" in data
    assert "audit" in data
    # In dry-run, should return planned ops
    if data["output"]:
        assert "planned_ops" in data["output"] or "simulated" in data["output"]

