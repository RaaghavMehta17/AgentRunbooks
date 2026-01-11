#!/bin/bash
# Automated demo script
# Requires: GITHUB_TOKEN and GITHUB_DEFAULT_REPO in .env

set -e

echo "🚀 Starting End-to-End Demo..."
echo ""

# Check prerequisites
if [ -z "$GITHUB_TOKEN" ]; then
    echo "❌ GITHUB_TOKEN not set in .env"
    exit 1
fi

if [ -z "$GITHUB_DEFAULT_REPO" ]; then
    echo "❌ GITHUB_DEFAULT_REPO not set in .env"
    exit 1
fi

# Extract owner and repo
IFS='/' read -r OWNER REPO <<< "$GITHUB_DEFAULT_REPO"

# Login
echo "📝 Step 1: Logging in..."
TOKEN=$(curl -s -X POST http://localhost:8000/auth/oidc/dev-login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@example.com","groups":[]}' | jq -r .access_token)

if [ -z "$TOKEN" ] || [ "$TOKEN" == "null" ]; then
    echo "❌ Failed to get authentication token"
    exit 1
fi
echo "✅ Logged in successfully"

# Create runbook
echo ""
echo "📝 Step 2: Creating runbook..."
RUNBOOK_RESPONSE=$(curl -s -X POST http://localhost:8000/runbooks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"Incident Response Demo\",
    \"yaml\": \"name: Incident Response Demo\\nsteps:\\n  - name: Create GitHub Issue\\n    tool: github.create_issue\\n    input:\\n      owner: \\\"$OWNER\\\"\\n      repo: \\\"$REPO\\\"\\n      title: \\\"Incident: Service Degradation - Demo\\\"\\n      body: \\\"Automated incident ticket created by Ops Agents demo run\\n\\nThis is a demo runbook execution.\\\"\\n\"
  }")

RUNBOOK_ID=$(echo $RUNBOOK_RESPONSE | jq -r .id)
if [ -z "$RUNBOOK_ID" ] || [ "$RUNBOOK_ID" == "null" ]; then
    echo "❌ Failed to create runbook"
    echo "$RUNBOOK_RESPONSE" | jq .
    exit 1
fi
echo "✅ Created runbook: $RUNBOOK_ID"

# Create policy
echo ""
echo "📝 Step 3: Creating policy..."
POLICY_RESPONSE=$(curl -s -X POST http://localhost:8000/policies \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Demo Policy",
    "version": "v1",
    "yaml": "roles:\n  - Admin\n  - SRE\ntool_allowlist:\n  Admin: [github.*, pagerduty.*]\n  SRE: [github.create_issue, pagerduty.ack]\nbudgets:\n  max_cost_per_run_usd: 1.0\n"
  }')
echo "✅ Policy created/updated"

# Dry-run
echo ""
echo "📝 Step 4: Running dry-run (preview)..."
DRY_RUN_ID=$(curl -s -X POST http://localhost:8000/runs \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"runbook_id\": \"$RUNBOOK_ID\",
    \"mode\": \"dry-run\",
    \"context\": {\"env\": \"production\", \"caller\": \"admin@example.com\"}
  }" | jq -r .id)

echo "   Dry-run ID: $DRY_RUN_ID"
echo "   Waiting for dry-run to complete..."
sleep 5

DRY_RUN_STATUS=$(curl -s http://localhost:8000/runs/$DRY_RUN_ID \
  -H "Authorization: Bearer $TOKEN" | jq -r .status)
echo "   Dry-run status: $DRY_RUN_STATUS"

# Execute (real mode)
echo ""
echo "📝 Step 5: Executing runbook (real mode)..."
EXEC_RUN_ID=$(curl -s -X POST http://localhost:8000/runs \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"runbook_id\": \"$RUNBOOK_ID\",
    \"mode\": \"execute\",
    \"context\": {\"env\": \"production\", \"caller\": \"admin@example.com\"}
  }" | jq -r .id)

echo "   Execution ID: $EXEC_RUN_ID"
echo "   Waiting for execution to complete..."
sleep 8

# Check status
EXEC_STATUS=$(curl -s http://localhost:8000/runs/$EXEC_RUN_ID \
  -H "Authorization: Bearer $TOKEN" | jq -r .status)

echo "   Execution status: $EXEC_STATUS"

# Show results
echo ""
echo "📊 Step 6: Execution Results:"
curl -s http://localhost:8000/runs/$EXEC_RUN_ID \
  -H "Authorization: Bearer $TOKEN" | jq '{
    status,
    steps: [.steps[] | {name, status, tool: .tool}],
    metrics: .metrics
  }'

echo ""
echo "✅ Demo complete!"
echo ""
echo "📋 Next steps:"
echo "   1. Check GitHub repository for created issue: https://github.com/$GITHUB_DEFAULT_REPO/issues"
echo "   2. View run in UI: http://localhost:5173/runs/$EXEC_RUN_ID"
echo "   3. Check audit logs: http://localhost:5173/audit"
echo ""
echo "Run ID: $EXEC_RUN_ID"
echo "Runbook ID: $RUNBOOK_ID"

