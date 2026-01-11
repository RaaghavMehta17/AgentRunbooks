from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from opentelemetry import trace

from . import auth, runtime_checks
from ..types import AdapterResponse, ToolCall

tracer = trace.get_tracer(__name__)


async def invoke(call: ToolCall) -> AdapterResponse:
    """Real Kubernetes adapter with safe-by-default execution."""
    tool = call.get("name", "")
    args = call.get("input", {})
    dry_run = call.get("dryRun", True)
    idempotency_key = call.get("idempotencyKey")
    
    with tracer.start_as_current_span("k8s.adapter.invoke") as span:
        span.set_attribute("tool", tool)
        span.set_attribute("dry_run", dry_run)
        span.set_attribute("idempotency_key", idempotency_key or "")
        
        # Get Kubernetes clients (user_roles would come from context in real implementation)
        try:
            core_v1, apps_v1 = auth.get_client(user_roles=None)
        except Exception as e:
            return {
                "output": None,
                "audit": {
                    "adapter": "k8s.real",
                    "tool": tool,
                    "error": str(e),
                    "dryRun": dry_run,
                },
            }
        
        try:
            if tool == "k8s.drain_node":
                result = _drain_node(core_v1, args, dry_run, idempotency_key)
            elif tool == "k8s.cordon_node":
                result = _cordon_node(core_v1, args, dry_run, idempotency_key)
            elif tool == "k8s.uncordon_node":
                result = _uncordon_node(core_v1, args, dry_run, idempotency_key)
            elif tool == "k8s.restart_deployment":
                result = _restart_deployment(apps_v1, core_v1, args, dry_run, idempotency_key)
            else:
                raise ValueError(f"unknown tool: {tool}")
            
            span.set_attribute("success", True)
            return result
        except Exception as e:
            span.set_attribute("success", False)
            span.record_exception(e)
            return {
                "output": None,
                "audit": {
                    "adapter": "k8s.real",
                    "tool": tool,
                    "error": str(e),
                    "dryRun": dry_run,
                },
            }


def _drain_node(core_v1: Any, args: dict[str, Any], dry_run: bool, idempotency_key: str | None) -> AdapterResponse:
    """Drain a node: cordon + evict pods."""
    node_name = args["node"]
    evict = args.get("evict", True)
    force = args.get("force", False)
    
    # Runtime checks
    try:
        node = core_v1.read_node(node_name)
        runtime_checks.assert_env_allowed(node.metadata.labels)
    except Exception as e:
        if not dry_run:
            raise
        # In dry-run, continue with warning
    
    if dry_run:
        # Simulate: list pods that would be evicted
        try:
            pods = core_v1.list_pod_for_all_namespaces(field_selector=f"spec.nodeName={node_name}")
            pod_names = [p.metadata.name for p in pods.items]
            return {
                "output": {
                    "ok": True,
                    "simulated": True,
                    "planned_ops": [
                        f"kubectl cordon {node_name}",
                        f"kubectl drain {node_name} --ignore-daemonsets --delete-emptydir-data",
                    ],
                    "pods_to_evict": pod_names,
                },
                "audit": {
                    "adapter": "k8s.real",
                    "tool": "k8s.drain_node",
                    "node": node_name,
                    "dryRun": True,
                    "idempotencyKey": idempotency_key,
                },
            }
        except Exception:
            pass
    
    # Real execution
    # Check idempotency annotation
    if idempotency_key:
        try:
            node = core_v1.read_node(node_name)
            existing_key = node.metadata.annotations.get("ops-agents/idempotency")
            if existing_key == idempotency_key:
                return {
                    "output": {"ok": True, "idempotent": True, "message": "already executed"},
                    "audit": {
                        "adapter": "k8s.real",
                        "tool": "k8s.drain_node",
                        "node": node_name,
                        "idempotent": True,
                    },
                }
        except Exception:
            pass
    
    # Cordon first
    try:
        core_v1.patch_node(
            node_name,
            {"spec": {"unschedulable": True}},
        )
    except Exception as e:
        return {
            "output": None,
            "audit": {"adapter": "k8s.real", "tool": "k8s.drain_node", "error": str(e)},
        }
    
    # Evict pods
    evicted = []
    try:
        pods = core_v1.list_pod_for_all_namespaces(field_selector=f"spec.nodeName={node_name}")
        for pod in pods.items:
            if pod.metadata.namespace == "kube-system":
                continue  # Skip system pods
            try:
                core_v1.delete_namespaced_pod(pod.metadata.name, pod.metadata.namespace)
                evicted.append(f"{pod.metadata.namespace}/{pod.metadata.name}")
            except Exception:
                pass
    except Exception as e:
        pass  # Continue even if eviction fails
    
    # Add idempotency annotation
    if idempotency_key:
        try:
            core_v1.patch_node(
                node_name,
                {
                    "metadata": {
                        "annotations": {"ops-agents/idempotency": idempotency_key},
                    }
                },
            )
        except Exception:
            pass
    
    return {
        "output": {"ok": True, "evicted": evicted},
        "audit": {
            "adapter": "k8s.real",
            "tool": "k8s.drain_node",
            "node": node_name,
            "evicted_count": len(evicted),
            "idempotencyKey": idempotency_key,
        },
    }


def _cordon_node(core_v1: Any, args: dict[str, Any], dry_run: bool, idempotency_key: str | None) -> AdapterResponse:
    """Cordon a node (mark unschedulable)."""
    node_name = args["node"]
    
    # Runtime checks
    try:
        node = core_v1.read_node(node_name)
        runtime_checks.assert_env_allowed(node.metadata.labels)
    except Exception as e:
        if not dry_run:
            raise
    
    if dry_run:
        return {
            "output": {
                "ok": True,
                "simulated": True,
                "planned_ops": [f"kubectl cordon {node_name}"],
            },
            "audit": {
                "adapter": "k8s.real",
                "tool": "k8s.cordon_node",
                "node": node_name,
                "dryRun": True,
                "idempotencyKey": idempotency_key,
            },
        }
    
    # Real execution
    try:
        core_v1.patch_node(
            node_name,
            {"spec": {"unschedulable": True}},
        )
        return {
            "output": {"ok": True},
            "audit": {
                "adapter": "k8s.real",
                "tool": "k8s.cordon_node",
                "node": node_name,
                "idempotencyKey": idempotency_key,
            },
        }
    except Exception as e:
        return {
            "output": None,
            "audit": {"adapter": "k8s.real", "tool": "k8s.cordon_node", "error": str(e)},
        }


def _uncordon_node(core_v1: Any, args: dict[str, Any], dry_run: bool, idempotency_key: str | None) -> AdapterResponse:
    """Uncordon a node (mark schedulable)."""
    node_name = args["node"]
    
    if dry_run:
        return {
            "output": {
                "ok": True,
                "simulated": True,
                "planned_ops": [f"kubectl uncordon {node_name}"],
            },
            "audit": {
                "adapter": "k8s.real",
                "tool": "k8s.uncordon_node",
                "node": node_name,
                "dryRun": True,
                "idempotencyKey": idempotency_key,
            },
        }
    
    # Real execution
    try:
        core_v1.patch_node(
            node_name,
            {"spec": {"unschedulable": False}},
        )
        return {
            "output": {"ok": True},
            "audit": {
                "adapter": "k8s.real",
                "tool": "k8s.uncordon_node",
                "node": node_name,
                "idempotencyKey": idempotency_key,
            },
        }
    except Exception as e:
        return {
            "output": None,
            "audit": {"adapter": "k8s.real", "tool": "k8s.uncordon_node", "error": str(e)},
        }


def _restart_deployment(
    apps_v1: Any, core_v1: Any, args: dict[str, Any], dry_run: bool, idempotency_key: str | None
) -> AdapterResponse:
    """Restart a deployment by patching annotation."""
    namespace = args["namespace"]
    name = args["name"]
    
    # Runtime checks
    runtime_checks.assert_namespace_allowed(namespace)
    
    try:
        deploy = apps_v1.read_namespaced_deployment(name, namespace)
        runtime_checks.assert_env_allowed(deploy.metadata.labels)
    except Exception as e:
        if not dry_run:
            raise
    
    if dry_run:
        return {
            "output": {
                "ok": True,
                "simulated": True,
                "planned_ops": [
                    f"kubectl rollout restart deployment/{name} -n {namespace}",
                ],
            },
            "audit": {
                "adapter": "k8s.real",
                "tool": "k8s.restart_deployment",
                "namespace": namespace,
                "name": name,
                "dryRun": True,
                "idempotencyKey": idempotency_key,
            },
        }
    
    # Real execution
    # Check idempotency
    if idempotency_key:
        try:
            deploy = apps_v1.read_namespaced_deployment(name, namespace)
            existing_key = deploy.metadata.annotations.get("ops-agents/idempotency")
            if existing_key == idempotency_key:
                return {
                    "output": {"ok": True, "idempotent": True, "message": "already executed"},
                    "audit": {
                        "adapter": "k8s.real",
                        "tool": "k8s.restart_deployment",
                        "idempotent": True,
                    },
                }
        except Exception:
            pass
    
    # Restart by patching annotation
    restart_time = datetime.now(timezone.utc).isoformat()
    try:
        apps_v1.patch_namespaced_deployment(
            name,
            namespace,
            {
                "metadata": {
                    "annotations": {
                        "kubectl.kubernetes.io/restartedAt": restart_time,
                        "ops-agents/idempotency": idempotency_key or "",
                    }
                }
            },
        )
        return {
            "output": {"ok": True, "restarted_at": restart_time},
            "audit": {
                "adapter": "k8s.real",
                "tool": "k8s.restart_deployment",
                "namespace": namespace,
                "name": name,
                "restarted_at": restart_time,
                "idempotencyKey": idempotency_key,
            },
        }
    except Exception as e:
        return {
            "output": None,
            "audit": {"adapter": "k8s.real", "tool": "k8s.restart_deployment", "error": str(e)},
        }

