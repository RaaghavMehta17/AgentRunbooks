FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app:${PYTHONPATH}
WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY orchestrator/pyproject.toml /app/
RUN pip install --upgrade pip \
    && pip install --no-cache-dir .

COPY adapters /app/adapters
COPY gateway/app/agents /app/agents
COPY gateway/app/policy_engine.py /app/policy_engine.py
COPY orchestrator/app /app/app

CMD ["python", "-m", "app.worker"]

