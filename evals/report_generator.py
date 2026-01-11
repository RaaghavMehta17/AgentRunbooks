#!/usr/bin/env python3
"""Generate evaluation reports with before/after comparisons and scorecards."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from sqlalchemy import create_engine, text
except ImportError:
    print("❌ SQLAlchemy not installed. Install with: pip install sqlalchemy psycopg")
    sys.exit(1)


def fetch_eval_results(db_url: str, suite: str | None = None) -> list[dict[str, Any]]:
    """Fetch eval results from database."""
    engine = create_engine(db_url, future=True)
    with engine.connect() as conn:
        query = "SELECT * FROM eval_results"
        params = {}
        if suite:
            query += " WHERE suite = :suite"
            params["suite"] = suite
        query += " ORDER BY created_at DESC"
        result = conn.execute(text(query), params)
        rows = result.fetchall()
        return [dict(row._mapping) for row in rows]


def calculate_statistics(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate statistics from eval results."""
    if not results:
        return {}

    match_scores = [r["accuracy"] for r in results if r.get("accuracy") is not None]
    hallu_rates = [r["hallu_rate"] for r in results if r.get("hallu_rate") is not None]
    p95_latencies = [r["p95_ms"] for r in results if r.get("p95_ms") is not None]
    costs = [r["cost_usd"] for r in results if r.get("cost_usd") is not None]

    stats = {}
    if match_scores:
        stats["accuracy"] = {
            "mean": sum(match_scores) / len(match_scores),
            "min": min(match_scores),
            "max": max(match_scores),
            "count": len(match_scores),
        }
    if hallu_rates:
        stats["hallucination_rate"] = {
            "mean": sum(hallu_rates) / len(hallu_rates),
            "min": min(hallu_rates),
            "max": max(hallu_rates),
            "count": len(hallu_rates),
        }
    if p95_latencies:
        stats["p95_latency_ms"] = {
            "mean": sum(p95_latencies) / len(p95_latencies),
            "min": min(p95_latencies),
            "max": max(p95_latencies),
            "count": len(p95_latencies),
        }
    if costs:
        stats["cost_usd"] = {
            "mean": sum(costs) / len(costs),
            "min": min(costs),
            "max": max(costs),
            "count": len(costs),
        }

    return stats


def generate_scorecard(results: list[dict[str, Any]], thresholds: dict[str, Any]) -> dict[str, Any]:
    """Generate scorecard with pass/fail indicators."""
    scorecard = {
        "timestamp": datetime.now().isoformat(),
        "total_runs": len(results),
        "thresholds": thresholds,
        "metrics": {},
    }

    stats = calculate_statistics(results)
    
    # Accuracy scorecard
    if "accuracy" in stats:
        acc = stats["accuracy"]
        threshold = thresholds.get("min_accuracy", 0.8)
        scorecard["metrics"]["accuracy"] = {
            "mean": acc["mean"],
            "threshold": threshold,
            "status": "pass" if acc["mean"] >= threshold else "fail",
            "pass_rate": sum(1 for r in results if r.get("accuracy", 0) >= threshold) / len(results) if results else 0,
        }

    # Hallucination rate scorecard
    if "hallucination_rate" in stats:
        hallu = stats["hallucination_rate"]
        threshold = thresholds.get("max_hallucination_rate", 0.1)
        scorecard["metrics"]["hallucination_rate"] = {
            "mean": hallu["mean"],
            "threshold": threshold,
            "status": "pass" if hallu["mean"] <= threshold else "fail",
            "pass_rate": sum(1 for r in results if r.get("hallu_rate", 1) <= threshold) / len(results) if results else 0,
        }

    # Latency scorecard
    if "p95_latency_ms" in stats:
        latency = stats["p95_latency_ms"]
        threshold = thresholds.get("max_p95_latency_ms", 2000)
        scorecard["metrics"]["p95_latency_ms"] = {
            "mean": latency["mean"],
            "threshold": threshold,
            "status": "pass" if latency["mean"] <= threshold else "fail",
            "pass_rate": sum(1 for r in results if r.get("p95_ms", float("inf")) <= threshold) / len(results) if results else 0,
        }

    # Cost scorecard
    if "cost_usd" in stats:
        cost = stats["cost_usd"]
        threshold = thresholds.get("max_cost_usd", 1.0)
        scorecard["metrics"]["cost_usd"] = {
            "mean": cost["mean"],
            "threshold": threshold,
            "status": "pass" if cost["mean"] <= threshold else "fail",
            "pass_rate": sum(1 for r in results if r.get("cost_usd", float("inf")) <= threshold) / len(results) if results else 0,
        }

    # Overall status
    all_pass = all(m.get("status") == "pass" for m in scorecard["metrics"].values())
    scorecard["overall_status"] = "pass" if all_pass else "fail"

    return scorecard


def compare_before_after(before_results: list[dict[str, Any]], after_results: list[dict[str, Any]]) -> dict[str, Any]:
    """Compare before and after eval results."""
    before_stats = calculate_statistics(before_results)
    after_stats = calculate_statistics(after_results)

    comparison = {
        "before": before_stats,
        "after": after_stats,
        "improvements": {},
    }

    # Compare accuracy
    if "accuracy" in before_stats and "accuracy" in after_stats:
        before_mean = before_stats["accuracy"]["mean"]
        after_mean = after_stats["accuracy"]["mean"]
        comparison["improvements"]["accuracy"] = {
            "change": after_mean - before_mean,
            "change_pct": ((after_mean - before_mean) / before_mean * 100) if before_mean > 0 else 0,
            "improved": after_mean > before_mean,
        }

    # Compare hallucination rate
    if "hallucination_rate" in before_stats and "hallucination_rate" in after_stats:
        before_mean = before_stats["hallucination_rate"]["mean"]
        after_mean = after_stats["hallucination_rate"]["mean"]
        comparison["improvements"]["hallucination_rate"] = {
            "change": after_mean - before_mean,
            "change_pct": ((after_mean - before_mean) / before_mean * 100) if before_mean > 0 else 0,
            "improved": after_mean < before_mean,  # Lower is better
        }

    # Compare latency
    if "p95_latency_ms" in before_stats and "p95_latency_ms" in after_stats:
        before_mean = before_stats["p95_latency_ms"]["mean"]
        after_mean = after_stats["p95_latency_ms"]["mean"]
        comparison["improvements"]["p95_latency_ms"] = {
            "change": after_mean - before_mean,
            "change_pct": ((after_mean - before_mean) / before_mean * 100) if before_mean > 0 else 0,
            "improved": after_mean < before_mean,  # Lower is better
        }

    # Compare cost
    if "cost_usd" in before_stats and "cost_usd" in after_stats:
        before_mean = before_stats["cost_usd"]["mean"]
        after_mean = after_stats["cost_usd"]["mean"]
        comparison["improvements"]["cost_usd"] = {
            "change": after_mean - before_mean,
            "change_pct": ((after_mean - before_mean) / before_mean * 100) if before_mean > 0 else 0,
            "improved": after_mean < before_mean,  # Lower is better
        }

    return comparison


def generate_html_report(scorecard: dict[str, Any], comparison: dict[str, Any] | None = None) -> str:
    """Generate HTML report."""
    html = """<!DOCTYPE html>
<html>
<head>
    <title>Evaluation Report</title>
    <style>
        body { font-family: sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }
        h1 { color: #333; }
        h2 { color: #666; border-bottom: 2px solid #ddd; padding-bottom: 10px; }
        .scorecard { background: #f9f9f9; padding: 15px; margin: 10px 0; border-radius: 4px; }
        .metric { margin: 10px 0; }
        .status-pass { color: #28a745; font-weight: bold; }
        .status-fail { color: #dc3545; font-weight: bold; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #f8f9fa; }
        .improved { color: #28a745; }
        .degraded { color: #dc3545; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Evaluation Report</h1>
        <p>Generated: {timestamp}</p>
        
        <h2>Scorecard</h2>
        <div class="scorecard">
            <p><strong>Overall Status:</strong> <span class="status-{overall_status}">{overall_status}</span></p>
            <p><strong>Total Runs:</strong> {total_runs}</p>
        </div>
        
        <h2>Metrics</h2>
        {metrics_html}
        
        {comparison_html}
    </div>
</body>
</html>"""

    metrics_html = ""
    for metric_name, metric_data in scorecard.get("metrics", {}).items():
        status_class = f"status-{metric_data['status']}"
        metrics_html += f"""
        <div class="metric">
            <h3>{metric_name.replace('_', ' ').title()}</h3>
            <p>Mean: {metric_data['mean']:.4f}</p>
            <p>Threshold: {metric_data['threshold']}</p>
            <p>Status: <span class="{status_class}">{metric_data['status']}</span></p>
            <p>Pass Rate: {metric_data['pass_rate']:.2%}</p>
        </div>
        """

    comparison_html = ""
    if comparison:
        comparison_html = "<h2>Before/After Comparison</h2>"
        comparison_html += "<table>"
        comparison_html += "<tr><th>Metric</th><th>Before</th><th>After</th><th>Change</th><th>Status</th></tr>"
        
        for metric_name, improvement in comparison.get("improvements", {}).items():
            change_class = "improved" if improvement["improved"] else "degraded"
            status_text = "✓ Improved" if improvement["improved"] else "✗ Degraded"
            comparison_html += f"""
            <tr>
                <td>{metric_name.replace('_', ' ').title()}</td>
                <td>{comparison['before'].get(metric_name, {}).get('mean', 'N/A')}</td>
                <td>{comparison['after'].get(metric_name, {}).get('mean', 'N/A')}</td>
                <td class="{change_class}">{improvement['change']:+.4f} ({improvement['change_pct']:+.2f}%)</td>
                <td class="{change_class}">{status_text}</td>
            </tr>
            """
        comparison_html += "</table>"

    return html.format(
        timestamp=scorecard.get("timestamp", datetime.now().isoformat()),
        overall_status=scorecard.get("overall_status", "unknown"),
        total_runs=scorecard.get("total_runs", 0),
        metrics_html=metrics_html,
        comparison_html=comparison_html,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate evaluation reports")
    parser.add_argument("--db-url", required=True, help="Database URL")
    parser.add_argument("--suite", help="Filter by suite name")
    parser.add_argument("--output", default="eval-report.json", help="Output file (JSON)")
    parser.add_argument("--html", help="Output HTML file")
    parser.add_argument("--thresholds", help="Thresholds JSON file")
    parser.add_argument("--before-db-url", help="Before database URL for comparison")
    parser.add_argument("--before-suite", help="Before suite name for comparison")
    args = parser.parse_args()

    # Fetch results
    results = fetch_eval_results(args.db_url, args.suite)
    if not results:
        print("❌ No eval results found")
        sys.exit(1)

    # Load thresholds
    thresholds = {}
    if args.thresholds:
        with open(args.thresholds, "r") as f:
            thresholds = json.load(f)
    else:
        # Default thresholds
        thresholds = {
            "min_accuracy": 0.8,
            "max_hallucination_rate": 0.1,
            "max_p95_latency_ms": 2000,
            "max_cost_usd": 1.0,
        }

    # Generate scorecard
    scorecard = generate_scorecard(results, thresholds)

    # Compare if before data provided
    comparison = None
    if args.before_db_url:
        before_results = fetch_eval_results(args.before_db_url, args.before_suite)
        comparison = compare_before_after(before_results, results)

    # Generate report
    report = {
        "scorecard": scorecard,
        "statistics": calculate_statistics(results),
        "results": results,
    }
    if comparison:
        report["comparison"] = comparison

    # Write JSON report
    with open(args.output, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"✅ JSON report written to {args.output}")

    # Write HTML report if requested
    if args.html:
        html_content = generate_html_report(scorecard, comparison)
        with open(args.html, "w") as f:
            f.write(html_content)
        print(f"✅ HTML report written to {args.html}")

    # Print summary
    print("\n📊 Scorecard Summary:")
    print(f"   Overall Status: {scorecard['overall_status']}")
    print(f"   Total Runs: {scorecard['total_runs']}")
    for metric_name, metric_data in scorecard.get("metrics", {}).items():
        status_icon = "✅" if metric_data["status"] == "pass" else "❌"
        print(f"   {status_icon} {metric_name}: {metric_data['mean']:.4f} (threshold: {metric_data['threshold']})")


if __name__ == "__main__":
    main()

