#!/bin/bash
set -euo pipefail

CLUSTER_NAME="${CLUSTER_NAME:-ops-agents}"

echo "Deleting Kind cluster: $CLUSTER_NAME"
kind delete cluster --name "$CLUSTER_NAME"

echo "✅ Cluster deleted"

