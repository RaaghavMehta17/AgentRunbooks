import os

import pytest
from fastapi.testclient import TestClient

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client() -> TestClient:
    with TestClient(app) as tc:
        yield tc


def _create_runbook(client: TestClient) -> str:
    payload = {
        "name": "rb-tests",
        "yaml": "name: rb-tests\nsteps:\n  - name: s1\n    tool: pagerduty.ack\n    input: { incident_id: \"INC\" }",
    }
    resp = client.post("/runbooks", json=payload)
    assert resp.status_code == 201
    return resp.json()["id"]


def test_create_run_inserts_steps(client: TestClient) -> None:
    runbook_id = _create_runbook(client)
    resp = client.post(
        "/runs",
        json={
            "runbook_id": runbook_id,
            "mode": "execute",
            "context": {"env": "dev"},
            "shadow_expected": {"steps": ["s1"]},
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] in ["running", "succeeded"]
    assert body["steps"]
    assert body["steps"][0]["status"] in ["pending", "succeeded"]


def test_get_run_returns_steps(client: TestClient) -> None:
    runbook_id = _create_runbook(client)
    resp = client.post(
        "/runs",
        json={"runbook_id": runbook_id, "mode": "dry-run", "context": {"env": "dev"}},
    )
    run_id = resp.json()["id"]
    get_resp = client.get(f"/runs/{run_id}")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert "steps" in data
    assert len(data["steps"]) >= 1


def test_sse_emits_events(client: TestClient) -> None:
    runbook_id = _create_runbook(client)
    resp = client.post(
        "/runs",
        json={"runbook_id": runbook_id, "mode": "dry-run", "context": {"env": "dev"}},
    )
    run_id = resp.json()["id"]
    with client.stream("GET", f"/runs/{run_id}/events") as stream:
        first = next(stream.iter_lines())
    assert first
    assert b"event: step" in first

