# End-to-End Demo Script

Complete step-by-step guide for running a real-world demo with GitHub integration.

## Prerequisites

1. **Services running:**
   ```bash
   make dev-up
   cd ui && npm run dev
   ```

2. **API Keys configured:**
   - Add `GITHUB_TOKEN` to `.env` file
   - Add `GITHUB_DEFAULT_REPO` to `.env` file (e.g., "yourorg/yourrepo")

3. **Restart services:**
   ```bash
   make dev-down
   make dev-up
   ```

## Demo Flow: Incident Response → GitHub Issue Creation

### Step 1: Login and Get Token

```bash
# Login via dev-login
TOKEN=$(curl -s -X POST http://localhost:8000/auth/oidc/dev-login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@example.com","groups":[]}' | jq -r .access_token)

echo "Token: $TOKEN"
```

### Step 2: Create a Runbook

```bash
# Create incident response runbook
RUNBOOK_RESPONSE=$(curl -s -X POST http://localhost:8000/runbooks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Incident Response Demo",
    "yaml": "name: Incident Response Demo\nsteps:\n  - name: Create GitHub Issue\n    tool: github.create_issue\n    input:\n      owner: \"yourorg\"\n      repo: \"yourrepo\"\n      title: \"Incident: Service Degradation\"\n      body: \"Automated incident ticket created by Ops Agents\"\n  - name: Acknowledge in PagerDuty\n    tool: pagerduty.ack\n    input:\n      incident_id: \"INC123\"\n"
  }')

RUNBOOK_ID=$(echo $RUNBOOK_RESPONSE | jq -r .id)
echo "Created runbook: $RUNBOOK_ID"
```

### Step 3: Create a Policy

```bash
# Create policy for the demo
curl -s -X POST http://localhost:8000/policies \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Demo Policy",
    "version": "v1",
    "yaml": "roles:\n  - Admin\n  - SRE\ntool_allowlist:\n  Admin: [github.*, pagerduty.*]\n  SRE: [github.create_issue, pagerduty.ack]\nbudgets:\n  max_cost_per_run_usd: 1.0\n"
  }' | jq .
```

### Step 4: Dry-Run (Preview)

```bash
# Execute in dry-run mode to preview
DRY_RUN_ID=$(curl -s -X POST http://localhost:8000/runs \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"runbook_id\": \"$RUNBOOK_ID\",
    \"mode\": \"dry-run\",
    \"context\": {\"env\": \"production\", \"caller\": \"admin@example.com\"}
  }" | jq -r .id)

echo "Dry-run ID: $DRY_RUN_ID"

# Wait a moment
sleep 3

# Check dry-run results
curl -s http://localhost:8000/runs/$DRY_RUN_ID \
  -H "Authorization: Bearer $TOKEN" | jq .steps
```

### Step 5: Execute (Real Mode)

```bash
# Execute with real GitHub adapter
EXEC_RUN_ID=$(curl -s -X POST http://localhost:8000/runs \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"runbook_id\": \"$RUNBOOK_ID\",
    \"mode\": \"execute\",
    \"context\": {\"env\": \"production\", \"caller\": \"admin@example.com\"}
  }" | jq -r .id)

echo "Execution ID: $EXEC_RUN_ID"

# Wait for execution
sleep 5

# Check execution status
curl -s http://localhost:8000/runs/$EXEC_RUN_ID \
  -H "Authorization: Bearer $TOKEN" | jq '{status, steps: [.steps[] | {name, status, output}]}'
```

### Step 6: Verify GitHub Issue Created

1. Go to your GitHub repository
2. Check the "Issues" tab
3. You should see the issue created by the runbook

### Step 7: View in UI

1. Open http://localhost:5173
2. Login with dev-login
3. Navigate to "Executions" → Find your run
4. View step details and logs

## Screenshot Checklist

Take screenshots at these points:

1. **Dashboard** - Overview page showing runs
2. **Runbook Detail** - The created runbook page
3. **Dry-Run Results** - Steps preview before execution
4. **Run Execution** - Run in progress with steps
5. **Run Completed** - Final status with step results
6. **GitHub Issue** - The created issue in GitHub
7. **Analytics** - Metrics and charts
8. **Audit Logs** - Audit trail of actions

## Video Script (2-3 minutes)

### Introduction (15 seconds)
"Hi, I'm demonstrating OpsGenie-for-Agents, an enterprise agentic runbook platform. This system automates incident response and operations with AI-powered agents and policy guardrails."

### Problem Statement (20 seconds)
"Traditional runbooks require manual execution and are prone to human error. Our platform uses AI agents to plan and execute runbooks automatically, with policy guardrails to ensure safety."

### Demo Flow (90 seconds)
1. "Let me create a runbook for incident response..."
2. "First, I'll run it in dry-run mode to preview the steps..."
3. "Now I'll execute it with real integrations - notice it creates a GitHub issue..."
4. "Let me verify the issue was created in GitHub..."
5. "The system tracks all executions with full audit logs..."

### Key Features (30 seconds)
"Key features include: AI-powered planning, policy guardrails, shadow mode for validation, multi-tenant RBAC, and comprehensive observability."

### Conclusion (15 seconds)
"This demonstrates how we can automate operations safely with AI agents and policy enforcement. Thank you!"

## Troubleshooting

**Issue: GitHub API error**
- Check `GITHUB_TOKEN` is valid
- Verify token has `repo` scope
- Check `GITHUB_DEFAULT_REPO` format (owner/repo)

**Issue: Run stuck**
- Check logs: `make logs`
- Check Temporal UI: http://localhost:8233
- Verify services are running: `make status`

**Issue: Permission denied**
- Ensure user has Admin or SRE role
- Check policy allows the tools

