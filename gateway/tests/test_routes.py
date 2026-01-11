import os
from typing import Generator

import pytest
from fastapi.testclient import TestClient

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client


def test_health(client: TestClient) -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_create_and_list_policy(client: TestClient) -> None:
    payload = {"name": "default", "yaml": "tool_allowlist:\n  SRE: [github.rollback_release]", "version": "v1"}
    create_resp = client.post("/policies", json=payload)
    assert create_resp.status_code == 201
    body = create_resp.json()
    assert body["name"] == payload["name"]
    list_resp = client.get("/policies")
    assert list_resp.status_code == 200
    assert any(item["name"] == payload["name"] for item in list_resp.json())


def test_policy_conflict(client: TestClient) -> None:
    payload = {"name": "unique-policy", "yaml": "roles:\n  - OnCall", "version": "v1"}
    first = client.post("/policies", json=payload)
    assert first.status_code == 201
    second = client.post("/policies", json=payload)
    assert second.status_code == 409


def test_create_and_list_runbook(client: TestClient) -> None:
    payload = {
        "name": "rollback-release",
        "yaml": "name: rollback-release\nsteps:\n  - name: ack\n    tool: pagerduty.ack",
    }
    create_resp = client.post("/runbooks", json=payload)
    assert create_resp.status_code == 201
    body = create_resp.json()
    assert body["name"] == payload["name"]
    list_resp = client.get("/runbooks")
    assert list_resp.status_code == 200
    assert any(item["name"] == payload["name"] for item in list_resp.json())


def test_runbook_conflict(client: TestClient) -> None:
    payload = {"name": "unique-runbook", "yaml": "name: unique\nsteps: []"}
    first = client.post("/runbooks", json=payload)
    assert first.status_code == 201
    second = client.post("/runbooks", json=payload)
    assert second.status_code == 409


def test_tools_schema_validation(client: TestClient) -> None:
    resp = client.post(
        "/tools/plan",
        json={"tool": "github.rollback_release", "args": {"repo": "x"}, "dryRun": True},
    )
    assert resp.status_code == 422


def test_policy_guard_denies_role(client: TestClient) -> None:
    client.post(
        "/policies",
        json={
            "name": "default",
            "yaml": "tool_allowlist:\n  SRE: [github.rollback_release]",
            "version": "v2",
        },
    )
    resp = client.post(
        "/tools/plan",
        headers={"X-Roles": "Viewer"},
        json={"tool": "github.rollback_release", "args": {"repo": "org/service", "tag": "v1"}},
    )
    assert resp.status_code == 403


def test_tools_plan_allowed(client: TestClient) -> None:
    resp = client.post(
        "/tools/plan",
        headers={"X-Roles": "SRE"},
        json={"tool": "github.rollback_release", "args": {"repo": "org/service", "tag": "v1"}},
    )
    assert resp.status_code == 200
    assert resp.json()["willCall"] is True


def test_tools_invoke_mock_by_default(client: TestClient) -> None:
    resp = client.post(
        "/tools/invoke",
        headers={"X-Roles": "SRE"},
        json={"tool": "github.rollback_release", "args": {"repo": "org/service", "tag": "v1"}, "dryRun": True},
    )
    assert resp.status_code == 200
    assert resp.json().get("audit", {}).get("adapter") == "github.mock"


def test_metrics_endpoint(client: TestClient) -> None:
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "text/plain" in resp.headers.get("content-type", "")

