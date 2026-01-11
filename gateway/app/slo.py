"""SLO (Service Level Objective) management and evaluation."""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

import httpx
from prometheus_client.parser import text_string_to_metric_families


class SLOConfig:
    """Loads and manages SLO targets from configuration."""

    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            # Default to deploy/slo/slo.yaml relative to project root
            project_root = Path(__file__).parent.parent.parent.parent
            config_path = project_root / "deploy" / "slo" / "slo.yaml"
        self.config_path = Path(config_path)
        self.targets: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        """Load SLO targets from YAML file."""
        if not self.config_path.exists():
            return
        with open(self.config_path, "r") as f:
            data = yaml.safe_load(f)
            self.targets = data.get("targets", {})

    def get_targets(self) -> Dict[str, Dict[str, Any]]:
        """Get all SLO targets."""
        return self.targets

    def get_target(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a specific SLO target by name."""
        return self.targets.get(name)


class SLOEvaluator:
    """Evaluates SLOs against Prometheus metrics."""

    def __init__(self, prometheus_url: Optional[str] = None):
        self.prometheus_url = prometheus_url or os.getenv(
            "PROMETHEUS_URL", "http://prometheus.monitoring:9090"
        )
        self.config = SLOConfig()

    async def evaluate_sli(
        self, target_name: str, query: str, window_minutes: int = 5
    ) -> Optional[float]:
        """Evaluate a single SLI using Prometheus query."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.prometheus_url}/api/v1/query",
                    params={"query": query},
                )
                response.raise_for_status()
                data = response.json()
                if data.get("status") == "success" and data.get("data", {}).get("result"):
                    result = data["data"]["result"][0]
                    value = float(result.get("value", [None, None])[1])
                    return value
        except Exception as e:
            print(f"Error evaluating SLI {target_name}: {e}")
        return None

    async def check_status(self, check_canary: bool = False) -> Dict[str, Any]:
        """Check current SLO status and return ok/failure reasons."""
        reasons: List[str] = []
        all_ok = True

        targets = self.config.get_targets()
        for name, target in targets.items():
            sli_query = target.get("sli")
            if not sli_query:
                continue

            objective = target.get("objective") or target.get("objective_ms")
            if objective is None:
                continue

            # Evaluate SLI
            value = await self.evaluate_sli(name, sli_query)
            if value is None:
                reasons.append(f"{name}: Could not evaluate SLI")
                all_ok = False
                continue

            # Check if objective is met
            if "objective_ms" in target:
                # Latency target (lower is better)
                if value > objective:
                    all_ok = False
                    reasons.append(
                        f"{name}: p95 latency {value:.1f}ms exceeds target {objective}ms"
                    )
            else:
                # Success rate target (higher is better)
                if value < objective:
                    all_ok = False
                    reasons.append(
                        f"{name}: success rate {value:.4f} below target {objective}"
                    )

        return {"ok": all_ok, "reasons": reasons, "timestamp": datetime.utcnow().isoformat()}


# Global instance
_slo_config: Optional[SLOConfig] = None
_slo_evaluator: Optional[SLOEvaluator] = None


def get_slo_config() -> SLOConfig:
    """Get or create SLO config singleton."""
    global _slo_config
    if _slo_config is None:
        _slo_config = SLOConfig()
    return _slo_config


def get_slo_evaluator() -> SLOEvaluator:
    """Get or create SLO evaluator singleton."""
    global _slo_evaluator
    if _slo_evaluator is None:
        _slo_evaluator = SLOEvaluator()
    return _slo_evaluator

