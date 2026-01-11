from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import create_engine, text
from datetime import datetime


def ensure_runbook(api: str, token: str) -> str:
    rb = {
        "name": "rollback-release",
        "yaml": "name: rollback-release\nsteps:\n  - name: ack-page\n    tool: pagerduty.ack\n    input: { incident_id: \"INC123\" }\n  - name: drain-node\n    tool: k8s.drain_node\n    input: { node: \"ip-10-0-1-23\", evict: true, force: false }\n    requires_approval: true\n  - name: rollback\n    tool: github.rollback_release\n    input: { repo: \"org/service\", tag: \"v1.2.2\" }\n",
    }
    headers = {"authorization": f"Bearer {token}", "content-type": "application/json"}
    r = httpx.post(f"{api}/runbooks", json=rb, headers=headers)
    if r.status_code not in (200, 201, 409):
        r.raise_for_status()
    if r.status_code == 409:
        lst = httpx.get(f"{api}/runbooks").json()
        for item in lst:
            if item["name"] == rb["name"]:
                return item["id"]
    return r.json()["id"]


def ensure_policy(api: str, token: str) -> None:
    pol = {
        "name": "default",
        "version": "v1",
        "yaml": "tool_allowlist:\n  Admin: [github.rollback_release, k8s.drain_node, pagerduty.ack]\n  SRE: [github.rollback_release, k8s.drain_node, pagerduty.ack]\napprovals:\n  - step: drain-node\n    required_roles: [OnCall]\n",
    }
    headers = {"authorization": f"Bearer {token}", "content-type": "application/json"}
    r = httpx.post(f"{api}/policies", json=pol, headers=headers)
    if r.status_code not in (200, 201, 409):
        r.raise_for_status()


def poll_run(api: str, run_id: str) -> dict[str, Any]:
    deadline = time.time() + 60
    while time.time() < deadline:
        data = httpx.get(f"{api}/runs/{run_id}").json()
        steps = data.get("steps", [])
        if all(s["status"] in {"succeeded", "failed", "skipped", "compensated"} for s in steps):
            return data
        time.sleep(2)
    return data


def insert_eval_result(db_url: str, name: str, run_id: str, accuracy: float, hallu: float, p95_ms: float, cost_usd: float = 0.0, suite: str = "smoke", tenant_id: str = "default", project_id: str | None = None) -> None:
    engine = create_engine(db_url, future=True)
    with engine.begin() as conn:
        # Check if tenant exists, create if not
        tenant_check = conn.execute(text("SELECT id FROM tenants WHERE id = :id"), {"id": tenant_id}).first()
        if not tenant_check:
            conn.execute(text("INSERT INTO tenants (id, name) VALUES (:id, :name) ON CONFLICT DO NOTHING"), {"id": tenant_id, "name": tenant_id})
        
        conn.execute(
            text(
                "INSERT INTO eval_results (id, name, run_id, accuracy, hallu_rate, p95_ms, cost_usd, suite, tenant_id, project_id) "
                "VALUES (:id, :name, :run_id, :accuracy, :hallu_rate, :p95_ms, :cost_usd, :suite, :tenant_id, :project_id)"
            ),
            {
                "id": os.urandom(8).hex(),
                "name": name,
                "run_id": run_id,
                "accuracy": accuracy,
                "hallu_rate": hallu,
                "p95_ms": p95_ms,
                "cost_usd": cost_usd,
                "suite": suite,
                "tenant_id": tenant_id,
                "project_id": project_id,
            },
        )


def detect_hallucination(result_steps: list[dict], expected_steps: list[dict]) -> float:
    """Detect hallucination rate by comparing expected vs actual steps."""
    if not expected_steps:
        return 0.0
    
    expected_tools = {step.get("tool") for step in expected_steps if isinstance(step, dict) and "tool" in step}
    actual_tools = {step.get("tool") for step in result_steps if step.get("tool")}
    
    if not expected_tools:
        return 0.0
    
    # Hallucination = tools used that weren't expected
    unexpected_tools = actual_tools - expected_tools
    hallucination_rate = len(unexpected_tools) / len(expected_tools) if expected_tools else 0.0
    
    return min(hallucination_rate, 1.0)


def calculate_cost(result: dict) -> float:
    """Calculate total cost from run metrics."""
    metrics = result.get("metrics", {})
    return metrics.get("cost_usd", 0.0)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", required=True)
    parser.add_argument("--token", required=True)
    parser.add_argument("--suite", default="smoke")
    parser.add_argument("--threshold-match", type=float, default=0.0)
    parser.add_argument("--threshold-viol", type=int, default=0)
    parser.add_argument("--threshold-hallu", type=float, default=1.0, help="Max hallucination rate")
    parser.add_argument("--threshold-cost", type=float, default=float("inf"), help="Max cost USD")
    parser.add_argument("--threshold-latency", type=float, default=float("inf"), help="Max p95 latency ms")
    args = parser.parse_args()

    api = args.api.rstrip("/")
    token = args.token
    db_url = os.getenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")

    cases_dir = Path(__file__).parent / "cases"
    # Load all test cases, or filter by suite if specified
    if args.suite == "smoke":
        cases = [cases_dir / "smoke_rollback.json"]
    elif args.suite == "all":
        cases = list(cases_dir.glob("*.json"))
    else:
        cases = [cases_dir / f"{args.suite}.json"] if (cases_dir / f"{args.suite}.json").exists() else []

    if not cases:
        print(f"❌ No test cases found for suite: {args.suite}")
        sys.exit(1)

    ensure_policy(api, token)
    runbook_id = ensure_runbook(api, token)

    all_passed = True
    for case_path in cases:
        case = json.loads(case_path.read_text())
        case_name = case.get("name", case_path.stem)
        print(f"\n📋 Running test case: {case_name}")
        
        payload = {
            "runbook_id": runbook_id,
            "mode": case["mode"],
            "context": {"env": "dev", "caller": "eval"},
        }
        
        # Add shadow_expected if mode is shadow
        if case["mode"] == "shadow" and "expected" in case:
            payload["shadow_expected"] = case["expected"]
        
        headers = {"authorization": f"Bearer {token}", "content-type": "application/json"}
        resp = httpx.post(f"{api}/runs", json=payload, headers=headers)
        resp.raise_for_status()
        run_id = resp.json()["id"]
        result = poll_run(api, run_id)
        
        # Extract metrics
        metrics = result.get("metrics", {})
        shadow = metrics.get("shadow", {})
        match_score = float(shadow.get("match_score", 0.0)) if shadow else 0.0
        policy_violations = shadow.get("policy_violations", 0) if shadow else 0
        
        steps = result.get("steps", [])
        durations = []
        for s in steps:
            start = s.get("started_at")
            end = s.get("ended_at")
            if start and end:
                try:
                    start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
                    end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
                    durations.append(max(0, (end_dt - start_dt).total_seconds() * 1000))
                except Exception:
                    continue
        p95_ms = max(durations) if durations else 0
        
        # Calculate hallucination rate
        expected_steps = case.get("expected", {}).get("steps", []) if case.get("mode") == "shadow" else []
        hallu_rate = detect_hallucination(steps, expected_steps)
        
        # Calculate cost
        cost_usd = calculate_cost(result)
        
        # Insert eval result
        insert_eval_result(db_url, case_name, run_id, match_score, hallu_rate, p95_ms, cost_usd, args.suite)
        
        print(f"   Match Score: {match_score:.2f}")
        print(f"   Hallucination Rate: {hallu_rate:.2f}")
        print(f"   Policy Violations: {policy_violations}")
        print(f"   P95 Latency: {p95_ms:.0f}ms")
        print(f"   Cost: ${cost_usd:.4f}")
        
        # Check thresholds
        failed = False
        if match_score < args.threshold_match:
            print(f"   ❌ ERROR: match_score {match_score:.2f} < threshold {args.threshold_match}")
            failed = True
        if policy_violations > args.threshold_viol:
            print(f"   ❌ ERROR: policy_violations {policy_violations} > threshold {args.threshold_viol}")
            failed = True
        if hallu_rate > args.threshold_hallu:
            print(f"   ❌ ERROR: hallucination_rate {hallu_rate:.2f} > threshold {args.threshold_hallu}")
            failed = True
        if cost_usd > args.threshold_cost:
            print(f"   ❌ ERROR: cost {cost_usd:.4f} > threshold {args.threshold_cost}")
            failed = True
        if p95_ms > args.threshold_latency:
            print(f"   ❌ ERROR: p95_latency {p95_ms:.0f}ms > threshold {args.threshold_latency:.0f}ms")
            failed = True
        
        if failed:
            all_passed = False
    
    if not all_passed:
        print("\n❌ Some test cases failed thresholds")
        sys.exit(1)
    else:
        print("\n✅ All test cases passed")


if __name__ == "__main__":
    main()

