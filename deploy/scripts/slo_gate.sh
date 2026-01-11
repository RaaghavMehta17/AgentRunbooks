#!/bin/bash
# SLO gate script for CI/CD when Argo Rollouts is disabled
# Exits with non-zero if SLO burn rate thresholds are exceeded

set -euo pipefail

PROMETHEUS_URL="${PROMETHEUS_URL:-http://prometheus.monitoring:9090}"
NAMESPACE="${NAMESPACE:-ops-agents}"
JOB_NAME="${JOB_NAME:-ops-agents-gateway}"
BURN_RATE_THRESHOLD="${BURN_RATE_THRESHOLD:-6}"
WINDOW="${WINDOW:-2h}"

echo "Checking SLO burn rate for ${JOB_NAME} in namespace ${NAMESPACE}..."

# Query error rate
ERROR_RATE_QUERY="sum(rate(http_requests_total{status=~\"5..\",job=\"${JOB_NAME}\",namespace=\"${NAMESPACE}\"}[${WINDOW}])) / sum(rate(http_requests_total{job=\"${JOB_NAME}\",namespace=\"${NAMESPACE}\"}[${WINDOW}]))"
ERROR_RATE=$(curl -s "${PROMETHEUS_URL}/api/v1/query" \
  --data-urlencode "query=${ERROR_RATE_QUERY}" | \
  jq -r '.data.result[0].value[1] // "0"')

if [ -z "$ERROR_RATE" ] || [ "$ERROR_RATE" == "null" ]; then
  echo "WARNING: Could not query error rate from Prometheus"
  exit 1
fi

# Calculate burn rate multiplier (error rate / error budget)
# For 99.5% SLO, error budget is 0.5% = 0.005
ERROR_BUDGET=0.005
BURN_RATE=$(echo "scale=2; ${ERROR_RATE} / ${ERROR_BUDGET}" | bc)

echo "Error rate: ${ERROR_RATE}"
echo "Burn rate multiplier: ${BURN_RATE}"

# Check threshold
if (( $(echo "${BURN_RATE} > ${BURN_RATE_THRESHOLD}" | bc -l) )); then
  echo "ERROR: Burn rate ${BURN_RATE} exceeds threshold ${BURN_RATE_THRESHOLD}"
  echo "Deployment gate failed - SLO error budget is burning too fast"
  exit 1
fi

echo "SLO gate passed - burn rate ${BURN_RATE} is within threshold"
exit 0

