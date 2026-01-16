# AgentRunbook

**Enterprise Agentic Runbook Platform** - Automate incident response, deployments, and operations with AI-powered agents and policy guardrails.

OpsGenie-for-Agents is a comprehensive platform that enables organizations to automate their operational runbooks using AI-powered agents. The system provides intelligent planning, execution, and policy enforcement for complex operational workflows across multiple integrated services.


## Problem & Motivation

Modern operations teams face increasing complexity in managing incident response, deployments, and operational workflows. Traditional approaches suffer from:

- **Manual execution errors** - Human operators make mistakes under pressure
- **Inconsistent procedures** - Runbooks are often outdated or inconsistently followed
- **Limited scalability** - Manual processes don't scale with growing infrastructure
- **Lack of intelligence** - No adaptive planning based on context or historical data
- **Compliance gaps** - Difficult to audit and enforce policy compliance

OpsGenie-for-Agents solves these challenges by providing:

- **AI-powered automation** - Intelligent agents that plan and execute runbooks adaptively
- **Policy guardrails** - Built-in RBAC, tool allowlists, and budget enforcement
- **Shadow mode** - Test agent plans against human outcomes before production
- **Complete auditability** - Immutable audit logs with hash chain verification
- **Multi-tenant isolation** - Secure, isolated execution environments
- **Real integrations** - Support for GitHub, Jira and more to come

---

## Features

### AI-Powered Agentic Execution
- **3-Agent Architecture** - Planner, Toolcaller, and Reviewer agents work together for intelligent execution
- **LLM Integration** - Supports OpenAI GPT-4 and Anthropic Claude
- **Context-Aware Planning** - Agents adapt plans based on environment, history, and context
- **Cost Tracking** - Real-time token usage and cost monitoring

### Policy & Governance
- **YAML-Based Policies** - Declarative, versioned policies stored in Git
- **Tool Allowlists** - Role-based restrictions on which tools can be executed
- **Budget Enforcement** - Per-run cost and token limits
- **Preconditions** - Conditional policy decisions based on context
- **Approval Workflows** - Built-in approval gates for sensitive operations

### Shadow Mode & Testing
- **Shadow Execution** - Compare agent plans against expected human outcomes
- **Match Scoring** - Quantify how well agent plans match expectations
- **Hallucination Detection** - Identify unexpected tool calls or steps
- **Evaluation Suite** - Comprehensive test harness with accuracy, latency, and cost metrics

### Real Integrations
- **GitHub** - Create issues, revert PRs, rollback releases
- **Jira** - Create issues, transition tickets, add comments
- **Kubernetes** - Cordon/drain nodes, restart deployments, check health
- **PagerDuty** - Acknowledge incidents, manage on-call

### Observability & Compliance
- **Prometheus Metrics** - Application and business metrics
- **OpenTelemetry Traces** - Distributed tracing across services
- **Grafana Dashboards** - Pre-configured visualization dashboards
- **Audit Logging** - Immutable audit trail with HMAC chain verification
- **Secret Redaction** - Automatic redaction of secrets in logs

## Architecture

The platform follows a microservices architecture with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (React)                         │
│  - Runbook Management UI                                        │
│  - Run Execution Dashboard                                      │
│  - Policy Editor                                                │
│  - Analytics & Reports                                          │
│  - Real-time Updates via SSE                                    │
└────────────────────┬────────────────────────────────────────────┘
                     │ HTTP/SSE
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Gateway (FastAPI)                          │
│  - REST API Endpoints                                           │
│  - Authentication & Authorization (RBAC)                        │
│  - Policy Loading & Enforcement                                 │
│  - Audit Logging                                                │
│  - Rate Limiting                                                │
│  - Tool Invocation                                              │
└──────────────┬──────────────────────────────┬───────────────────┘
               │                              │
               ▼                              ▼
    ┌──────────────────┐          ┌──────────────────────┐
    │   PostgreSQL     │          │   Temporal Server    │
    │   + pgvector     │          │   (Workflow Engine)  │
    │                  │          └──────────┬───────────┘
    │  - Runbooks      │                     │
    │  - Policies      │                     ▼
    │  - Runs          │          ┌──────────────────────┐
    │  - Steps         │          │   Orchestrator       │
    │  - Audit Logs    │          │   (Temporal Worker)  │
    │  - Eval Results  │          │                      │
    │  - Tenants       │          │  - Step Planning     │
    │  - Projects      │          │  - Policy Validation │
    └──────────────────┘          │  - Adapter Invocation│
                                  │  - Shadow Comparison │
                                  └──────────┬───────────┘
                                             │
                    ┌───────────────────────┼───────────────────────┐
                    │                       │                       │
                    ▼                       ▼                       ▼
        ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
        │ GitHub Adapter  │    │  Jira Adapter   │    │  K8s Adapter    │
        │                 │    │                 │    │                 │
        │ - create_issue  │    │ - create_issue  │    │ - cordon_node   │
        │ - revert_pr     │    │ - transition    │    │ - drain_node    │
        │ - rollback      │    │ - comment       │    │ - restart_deploy│
        └─────────────────┘    └─────────────────┘    └─────────────────┘
                    │                       │                       │
                    └───────────────────────┼───────────────────────┘
                                            │
                                            ▼
                            ┌───────────────────────────┐
                            │   External Services       │
                            │   GitHub, Jira, K8s, PD   │
                            └───────────────────────────┘
```

### Data Flow

1. **User creates/triggers runbook** via UI or API
2. **Gateway validates** request (auth, RBAC, policy)
3. **Gateway creates Run record** in database
4. **Gateway starts Temporal workflow** (async)
5. **Orchestrator worker** picks up workflow
6. **Orchestrator plans steps** using agent brain (LLM)
7. **For each step:**
   - Validate against policy (tool allowlist, budgets)
   - Check for approvals if required
   - Invoke adapter (GitHub, Jira, K8s, etc.)
   - Record step results
8. **Orchestrator updates Run** status and metrics
9. **Gateway streams updates** to frontend via SSE
10. **Run completes** (succeeded/failed)

## Technology Stack

### Backend
- **Framework**: FastAPI 0.115+ (Python 3.12+)
- **ORM**: SQLAlchemy 2.0+
- **Validation**: Pydantic 2.8+
- **Database**: PostgreSQL 16 with pgvector extension
- **Workflow Engine**: Temporal 1.7+ (Python SDK)

### Frontend
- **Framework**: React 18.2+
- **Language**: TypeScript 5.3+
- **Styling**: Tailwind CSS 3.3+
- **Routing**: React Router 6.20+
- **UI Components**: Headless UI 2.2+
- **Charts**: Recharts 3.6+

### Infrastructure
- **Containerization**: Docker, Docker Compose
- **Orchestration**: Kubernetes (Helm charts included)
- **Service Discovery**: DNS-based (Docker Compose) / K8s Services

---

## Key Components

### Gateway Service

The Gateway is the primary API service that handles all HTTP requests.

**Responsibilities:**
- REST API endpoints for all resources (runbooks, runs, policies, etc.)
- Authentication & authorization via RBAC middleware
- Policy loading and validation
- Audit logging with hash chain verification
- Rate limiting per subject
- Tool invocation endpoints (`/tools/plan`, `/tools/invoke`)
- Real-time updates via Server-Sent Events (SSE)

**Technology:**
- FastAPI with async/await support
- SQLAlchemy for database access
- Pydantic for request/response validation
- OpenTelemetry for instrumentation

**Key Endpoints:**
- `/runbooks` - Runbook CRUD operations
- `/runs` - Run execution and status
- `/policies` - Policy management
- `/tools/*` - Tool planning and invocation
- `/approvals` - Approval workflow management
- `/analytics` - Metrics and analytics
- `/audit` - Audit log queries
- `/healthz` - Health check

### Orchestrator Service

The Orchestrator is a Temporal worker that executes runbook workflows.

**Responsibilities:**
- Workflow execution via Temporal
- Step planning using agent brain (LLM)
- Policy validation before each step
- Adapter invocation (GitHub, Jira, K8s, PagerDuty)
- Shadow mode comparison (agent vs expected)
- Compensation logic on failures
- Metrics aggregation (tokens, cost, latency)

**Key Activities:**
- `plan_step` - Agent planning via LLM
- `invoke_adapter` - Tool execution
- `wait_for_approval` - Approval workflow handling
- `compute_shadow` - Shadow mode comparison
- `update_run_totals` - Metrics aggregation

### Frontend (React UI)

A modern single-page application for managing runbooks and monitoring executions.

**Key Pages:**
- **Dashboard** - Overview of runs, metrics, and status
- **Runbooks** - Create, edit, and manage runbook definitions
- **Runs** - View execution history and real-time status
- **Policies** - Define and manage policy rules
- **Approvals** - Approve or deny pending requests
- **Analytics** - Charts and reports on execution metrics
- **Settings** - User preferences and system configuration

Runbook YAML + Context
        │
        ▼
┌───────────────────┐
│  Planner Agent    │ ← Uses LLM to analyze and plan
│  (GPT-4/Claude)   │
└─────────┬─────────┘
          │
          ▼
    Planned Steps
          │
          ▼
┌───────────────────┐
│ Toolcaller Agent  │ ← Uses LLM to refine tools/args
│  (GPT-4/Claude)   │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ Reviewer Agent    │ ← Uses LLM to validate against policy
│  (GPT-4/Claude)   │
└─────────┬─────────┘
          │
          ▼
    Allow/Block/Approve
          │
          ▼
    Execute Step
```

### Enabling AI Mode

By default, the system runs in **stub mode** (deterministic, no AI) for testing without API costs.

To enable real AI-powered execution:

**Option 1: OpenAI (Recommended for Demo)**

```bash
# Add to .env file:
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-openai-api-key-here
COST_MODEL=openai_gpt-4o
TOKEN_PRICE_INPUT_USD=0.000005
TOKEN_PRICE_OUTPUT_USD=0.000015
```

**Option 2: Anthropic Claude**

```bash
# Add to .env file:
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-your-anthropic-api-key-here
```

After adding keys, restart services:
```bash
make dev-down
make dev-up
```
---

## Quick Start

### Prerequisites

- **Docker Desktop** (or Docker Engine + Docker Compose)
- **Node.js** 18+ and npm (for frontend development)
- **Python** 3.12+ (optional, for running tests locally)

### Installation

1. **Clone the repository**

```bash
git clone https://github.com/RaaghavMehta17/AgentRunbooks.git
cd AgentRunbooks
```

2. **Create environment file**

```bash
cp .env.example .env
# Edit .env and add your API keys if using real AI/integrations
```

3. **Start backend services**

```bash
make dev-up
```

This starts:
- PostgreSQL database 
- Temporal server 
- Temporal UI 
- Gateway API 
- Orchestrator worker
- Prometheus 
- Grafana 
- OpenTelemetry Collector

4. **Install and start frontend**

```bash
cd ui
npm install
npm run dev
```

Frontend will be available at `http://localhost:5173`

5. **Verify installation**

```bash
# Check health
curl http://localhost:8000/healthz

# Check service status
make status

# Run diagnostics
make doctor
```

### Access Points

- **Frontend UI**: http://localhost:5173
- **Gateway API**: http://localhost:8000
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **Temporal UI**: http://localhost:8233

---

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# Database
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=ops_agents

# Temporal
TEMPORAL_HOST=temporal:7233
TEMPORAL_NAMESPACE=default

# Observability
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317

# AI/LLM (optional - defaults to stub mode)
LLM_PROVIDER=stub  # or "openai" or "anthropic"
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
COST_MODEL=openai_gpt-4o
TOKEN_PRICE_INPUT_USD=0.000005
TOKEN_PRICE_OUTPUT_USD=0.000015

# OIDC SSO (optional)
OIDC_CLIENT_ID=...
OIDC_CLIENT_SECRET=...
OIDC_ISSUER_URL=https://your-oidc-provider.com

# Integration API Keys (optional - for real adapters)
GITHUB_TOKEN=ghp_...
JIRA_API_TOKEN=...
PAGERDUTY_API_KEY=...
KUBERNETES_CONFIG_PATH=/path/to/kubeconfig

# Feature Flags
USE_REAL_GITHUB=false
USE_REAL_JIRA=false
USE_REAL_K8S=false
USE_REAL_PAGERDUTY=false
```
## Development

### Project Structure

```
.
├── gateway/              # FastAPI backend service
│   ├── app/             # Application code
│   │   ├── routers/     # API route handlers
│   │   ├── agents/      # AI agent system
│   │   ├── billing/     # Billing and quotas
│   │   ├── models.py    # SQLAlchemy models
│   │   └── schemas.py   # Pydantic schemas
│   ├── alembic/         # Database migrations
│   ├── tests/           # Backend tests
│   └── Dockerfile       # Gateway container
│
├── orchestrator/         # Temporal worker service
│   ├── app/             # Worker code
│   │   ├── workflows.py # Temporal workflows
│   │   └── activities.py # Temporal activities
│   └── Dockerfile       # Orchestrator container
│
├── ui/                   # React frontend
│   ├── src/
│   │   ├── components/  # React components
│   │   ├── pages/       # Page components
│   │   └── lib/         # Utilities
│   └── package.json
│
├── adapters/             # External service adapters
│   ├── github/          # GitHub adapter
│   ├── jira/            # Jira adapter
│   ├── k8s/             # Kubernetes adapter
│   └── pagerduty/       # PagerDuty adapter
│
├── evals/                # Evaluation harness
│   ├── harness.py       # Main evaluation script
│   ├── report_generator.py # Report generation
│   └── cases/           # Test cases
│
├── ops/                  # Docker Compose configuration
│   ├── docker-compose.yml
│   ├── prometheus.yml
│   └── grafana/         # Grafana provisioning
│
├── deploy/               # Deployment configurations
│   ├── helm/            # Helm charts
│   └── scripts/         # Deployment scripts
│
└── docs/                 # Documentation
    ├── ARCHITECTURE.md
    ├── DESIGN_CHOICES.md
    ├── SECURITY.md
    └── ...
```

OpsGenie-for-Agents is built with the following open-source technologies:

- **[FastAPI](https://fastapi.tiangolo.com/)** - Modern, fast web framework for building APIs
- **[Temporal](https://temporal.io/)** - Durable execution engine for workflows
- **[PostgreSQL](https://www.postgresql.org/)** + **[pgvector](https://github.com/pgvector/pgvector)** - Relational database with vector similarity search
- **[React](https://react.dev/)** + **[TypeScript](https://www.typescriptlang.org/)** - Modern frontend framework
- **[OpenTelemetry](https://opentelemetry.io/)** - Observability framework
- **[Prometheus](https://prometheus.io/)** + **[Grafana](https://grafana.com/)** - Metrics and visualization
- **[Tailwind CSS](https://tailwindcss.com/)** - Utility-first CSS framework



