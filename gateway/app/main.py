import logging

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest

from . import otel
from .db import init_db
from .middleware import auth_middleware
from .routers import analytics, approvals, audit, canary, evals, feature_flags, health, oidc, policies, projects, runbooks, runs, scim, settings, slo, tenant_export, tenants, tools
from .billing import routers as billing_routers

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="OpsGenie-for-Agents: Gateway", version="0.1.0")
otel.instrument(app)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth middleware (runs after CORS)
app.middleware("http")(auth_middleware)

http_requests_total = Counter(
    "http_requests_total",
    "HTTP requests by method and path",
    ["method", "path", "status"],
)


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.middleware("http")
async def record_requests(request: Request, call_next):
    response = await call_next(request)
    http_requests_total.labels(
        method=request.method, path=request.url.path, status=str(response.status_code)
    ).inc()
    return response


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


app.include_router(health.router)
app.include_router(analytics.router)
app.include_router(runbooks.router)
app.include_router(policies.router)
app.include_router(runs.router)
app.include_router(tools.router)
app.include_router(approvals.router)
app.include_router(evals.router)
app.include_router(tenants.router)
app.include_router(audit.router)
app.include_router(canary.router)
app.include_router(feature_flags.router)
app.include_router(oidc.router)
app.include_router(projects.router)
app.include_router(settings.router)
app.include_router(scim.router)
app.include_router(slo.router)
app.include_router(tenant_export.router)
app.include_router(billing_routers.router)

