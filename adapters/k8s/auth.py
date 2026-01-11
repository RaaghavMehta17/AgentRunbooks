from __future__ import annotations

import os
from typing import Any

from kubernetes import client, config
from kubernetes.client import CoreV1Api, AppsV1Api


def get_client(user_roles: list[str] | None = None) -> tuple[CoreV1Api, AppsV1Api]:
    """Get Kubernetes client based on K8S_MODE environment variable."""
    mode = os.getenv("K8S_MODE", "local")
    
    if mode == "sa":
        # Service account mode
        token = os.getenv("K8S_SA_TOKEN")
        ca_crt = os.getenv("K8S_SA_CA_CRT")
        host = os.getenv("K8S_HOST", "https://kubernetes.default.svc")
        
        if not token:
            raise RuntimeError("K8S_SA_TOKEN required when K8S_MODE=sa")
        
        configuration = client.Configuration()
        configuration.host = host
        configuration.ssl_ca_cert = ca_crt if ca_crt else None
        configuration.api_key_prefix["authorization"] = "Bearer"
        configuration.api_key["authorization"] = token
        
        core_v1 = client.CoreV1Api(client.ApiClient(configuration))
        apps_v1 = client.AppsV1Api(client.ApiClient(configuration))
        return core_v1, apps_v1
    
    elif mode == "kubeconfig":
        # Kubeconfig mode
        kubeconfig_path = os.getenv("K8S_KUBECONFIG", os.path.expanduser("~/.kube/config"))
        
        # Optionally select context based on user roles
        context = None
        if user_roles:
            rbac_map = _parse_rbac_map()
            for role in user_roles:
                if role in rbac_map:
                    context = rbac_map[role]
                    break
        
        config.load_kube_config(config_file=kubeconfig_path, context=context)
        core_v1 = client.CoreV1Api()
        apps_v1 = client.AppsV1Api()
        return core_v1, apps_v1
    
    else:
        # local mode: try in-cluster first, fallback to kubeconfig
        try:
            config.load_incluster_config()
            core_v1 = client.CoreV1Api()
            apps_v1 = client.AppsV1Api()
            return core_v1, apps_v1
        except config.ConfigException:
            # Fallback to kubeconfig
            kubeconfig_path = os.getenv("K8S_KUBECONFIG", os.path.expanduser("~/.kube/config"))
            config.load_kube_config(config_file=kubeconfig_path)
            core_v1 = client.CoreV1Api()
            apps_v1 = client.AppsV1Api()
            return core_v1, apps_v1


def _parse_rbac_map() -> dict[str, str]:
    """Parse K8S_RBAC_MAP from environment."""
    rbac_map_str = os.getenv("K8S_RBAC_MAP", "{}")
    try:
        import json
        return json.loads(rbac_map_str)
    except Exception:
        return {}

