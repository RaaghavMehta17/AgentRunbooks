from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    temporal_host: str = "temporal:7233"
    temporal_namespace: str = "default"
    otel_exporter_otlp_endpoint: str | None = None
    otel_service_name: str = "orchestrator"

    class Config:
        env_prefix = ""
        case_sensitive = False


