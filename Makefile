SHELL := /bin/bash

DEV_ENV ?= .env

.PHONY: dev-up dev-down dev-reset logs status ps

dev-up:
	@[ -f $(DEV_ENV) ] || cp .env.example $(DEV_ENV)
	cd ops && docker compose --env-file ../$(DEV_ENV) up --build -d

dev-down:
	cd ops && docker compose --env-file ../$(DEV_ENV) down

dev-reset:
	cd ops && docker compose --env-file ../$(DEV_ENV) down -v
	@echo "Volumes removed. Run 'make dev-up' to start fresh."

logs:
	cd ops && docker compose logs -f gateway

status:
	cd ops && docker compose ps

ps: status

.PHONY: otel-up tail-gateway tail-orch

otel-up:
	cd ops && docker compose up -d otel-collector prometheus grafana tempo temporal temporal-ui db gateway orchestrator

tail-gateway:
	cd ops && docker compose logs -f gateway

tail-orch:
	cd ops && docker compose logs -f orchestrator

.PHONY: backup

backup:
	@mkdir -p ops/backup
	@echo "Creating database backup..."
	@docker compose -f ops/docker-compose.yml exec -T db pg_dump -U postgres ops_agents > ops/backup/backup_$$(date +%Y%m%d_%H%M%S).sql || \
		docker compose -f ops/docker-compose.yml run --rm -T db pg_dump -h db -U postgres ops_agents > ops/backup/backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "Backup created in ops/backup/"

.PHONY: doctor

doctor:
	@echo "🏥 Running health diagnostics..."
	@echo ""
	@echo "=== Docker ==="
	@if command -v docker > /dev/null 2>&1; then \
		echo "✅ Docker is installed"; \
		if docker info > /dev/null 2>&1; then \
			echo "✅ Docker daemon is running"; \
		else \
			echo "❌ Docker daemon is not running. Please start Docker Desktop."; \
			exit 1; \
		fi; \
	else \
		echo "❌ Docker is not installed"; \
		exit 1; \
	fi
	@echo ""
	@echo "=== Environment ==="
	@if [ -f $(DEV_ENV) ]; then \
		echo "✅ .env file exists"; \
	else \
		echo "⚠️  .env file not found. Run: ./setup-local.sh"; \
	fi
	@echo ""
	@echo "=== Ports ==="
	@PORTS="8000 5173 5432 3000 9090 3200 7233 8233"; \
	for port in $$PORTS; do \
		if lsof -Pi :$$port -sTCP:LISTEN -t >/dev/null 2>&1; then \
			echo "⚠️  Port $$port is in use"; \
		else \
			echo "✅ Port $$port is available"; \
		fi; \
	done
	@echo ""
	@echo "=== Services ==="
	@cd ops && docker compose ps 2>/dev/null | grep -q "NAME" && docker compose ps || echo "⚠️  Services not running. Run: make dev-up"
	@echo ""
	@echo "=== Health Checks ==="
	@if curl -s http://localhost:8000/healthz > /dev/null 2>&1; then \
		echo "✅ Gateway is healthy (http://localhost:8000/healthz)"; \
	else \
		echo "❌ Gateway is not responding. Run: make dev-up"; \
	fi
	@echo ""
	@echo "✅ Diagnostics complete!"
