#!/bin/bash
set -euo pipefail

CLUSTER_NAME="${CLUSTER_NAME:-ops-agents}"
NAMESPACE="${NAMESPACE:-ops-agents}"

echo "Creating Kind cluster: $CLUSTER_NAME"

# Create Kind cluster config
cat <<EOF | kind create cluster --name "$CLUSTER_NAME" --config=-
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
name: $CLUSTER_NAME
nodes:
  - role: control-plane
    extraPortMappings:
      - containerPort: 80
        hostPort: 30080
        protocol: TCP
      - containerPort: 443
        hostPort: 30443
        protocol: TCP
EOF

echo "Waiting for cluster to be ready..."
kubectl wait --for=condition=Ready nodes --all --timeout=120s

echo "Installing NGINX Ingress Controller..."
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml

echo "Waiting for ingress-nginx to be ready..."
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=120s

echo "Creating namespace: $NAMESPACE"
kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -

echo "Installing Helm chart..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT" || exit

helm upgrade --install ops-agents \
  ./deploy/helm/ops-agents \
  --namespace "$NAMESPACE" \
  --create-namespace \
  --values ./deploy/helm/ops-agents/values-kind.yaml \
  --wait \
  --timeout 5m

echo ""
echo "✅ Cluster is ready!"
echo ""
echo "Add to /etc/hosts:"
echo "  127.0.0.1 ops-agents.local"
echo ""
echo "Smoke tests:"
echo "  # Health check"
echo "  curl -s http://ops-agents.local/healthz"
echo ""
echo "  # Port-forward for direct access"
echo "  kubectl -n $NAMESPACE port-forward deploy/ops-agents-gateway 8000:8000 &"
echo "  curl -s localhost:8000/healthz"
echo ""
echo "To delete the cluster:"
echo "  bash deploy/scripts/kind-down.sh"

